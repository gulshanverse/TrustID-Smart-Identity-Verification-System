import { CredibilityStrip, FeaturesSection, FinalCTA, Hero, HowItWorksSection, IntelligenceSection, ProblemSection, SecuritySection, SolutionSection, TechnologySection, UseCasesSection } from "@/components/marketing";
import { PublicFooter, PublicHeader } from "@/components/layouts";

export default function HomePage() {
  return <><PublicHeader /><main><Hero /><CredibilityStrip /><ProblemSection /><SolutionSection /><HowItWorksSection /><FeaturesSection /><IntelligenceSection /><SecuritySection /><UseCasesSection /><TechnologySection /><FinalCTA /></main><PublicFooter /></>;
}
