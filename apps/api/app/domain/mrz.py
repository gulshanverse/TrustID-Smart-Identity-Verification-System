from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MRZChecksum:
    field: str
    value: str
    check_digit: str | None
    valid: bool | None


@dataclass(frozen=True)
class MRZResult:
    detected: bool
    valid: bool
    raw_text: str
    normalized_text: str
    fields: dict[str, str | None]
    checksums: tuple[MRZChecksum, ...]
    reason: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {"mrz_detected": self.detected, "mrz_valid": self.valid, "mrz_raw_text": self.raw_text, "mrz_normalized_text": self.normalized_text, "mrz_fields": self.fields, "mrz_checksum_results": [item.__dict__ for item in self.checksums], "reason": self.reason}


def _normalize_line(line: str) -> str:
    return re.sub(r"[^A-Z0-9<]", "", line.upper().replace(" ", "<"))


def _check_digit(value: str, digit: str) -> bool:
    if not digit.isdigit():
        return False
    weights = (7, 3, 1)
    total = 0
    for index, char in enumerate(value):
        if char == "<":
            number = 0
        elif char.isdigit():
            number = int(char)
        elif "A" <= char <= "Z":
            number = ord(char) - 55
        else:
            return False
        total += number * weights[index % 3]
    return total % 10 == int(digit)


def _date(value: str, *, expiry: bool = False) -> str | None:
    if len(value) != 6 or not value.isdigit():
        return None
    year = 2000 + int(value[:2]) if expiry or int(value[:2]) < 30 else 1900 + int(value[:2])
    try:
        return date(year, int(value[2:4]), int(value[4:6])).isoformat()
    except ValueError:
        return None


def parse_td3(text: str) -> MRZResult:
    candidates = [line.strip() for line in text.splitlines() if line.strip()]
    pairs: list[tuple[str, str]] = []
    for index in range(len(candidates) - 1):
        first, second = _normalize_line(candidates[index]), _normalize_line(candidates[index + 1])
        if len(first) == 44 and len(second) == 44 and first.startswith("P"):
            pairs.append((first, second))
    if not pairs:
        return MRZResult(False, False, text, "", {}, (), "No TD3 passport MRZ candidate detected.")
    first, second = pairs[-1]
    surname_given = first[5:44].split("<<", 1)
    surname = surname_given[0].replace("<", " ").strip() or None
    given = surname_given[1].replace("<", " ").strip() if len(surname_given) > 1 else None
    checks = (
        MRZChecksum("document_number", second[0:9], second[9], _check_digit(second[0:9], second[9])),
        MRZChecksum("date_of_birth", second[13:19], second[19], _check_digit(second[13:19], second[19])),
        MRZChecksum("expiry_date", second[21:27], second[27], _check_digit(second[21:27], second[27])),
        MRZChecksum("personal_number", second[28:42], second[42], _check_digit(second[28:42], second[42])),
    )
    fields = {"document_type": first[0], "issuing_state": first[2:5], "surname": surname, "given_names": given, "document_number": second[0:9].replace("<", ""), "nationality": second[10:13], "date_of_birth": _date(second[13:19]), "sex": None if second[20] == "<" else second[20], "expiry_date": _date(second[21:27], expiry=True), "personal_number": second[28:42].replace("<", "") or None}
    return MRZResult(True, all(item.valid is True for item in checks), "\n".join(candidates[index] for index in range(len(candidates)) if _normalize_line(candidates[index]) in {first, second}), f"{first}\n{second}", fields, checks)


def compare_fields(visual_fields: dict[str, str | None], mrz: MRZResult) -> list[dict[str, str | None]]:
    results: list[dict[str, str | None]] = []
    mappings = {"full_name": "name", "passport_number": "document_number", "nationality": "nationality", "date_of_birth": "date_of_birth", "gender": "sex", "expiry_date": "expiry_date"}
    for visual_name, mrz_name in mappings.items():
        visual = visual_fields.get(visual_name)
        expected = " ".join(value for key in ("surname", "given_names") if (value := mrz.fields.get(key))) if mrz_name == "name" else mrz.fields.get(mrz_name)
        normalized_visual = re.sub(r"[^A-Z0-9]", "", (visual or "").upper())
        normalized_mrz = re.sub(r"[^A-Z0-9]", "", (expected or "").upper())
        status = "NOT_AVAILABLE" if not visual or not expected else "MATCH" if normalized_visual == normalized_mrz else "MISMATCH"
        results.append({"field": visual_name, "visual_value": visual, "mrz_value": expected, "status": status})
    return results
