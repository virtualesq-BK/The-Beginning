export const USAGE_PURPOSE_OPTIONS = [
  { value: "draft_writing", labelKey: "auth.usagePurpose.draftWriting" },
  { value: "negotiation_prep", labelKey: "auth.usagePurpose.negotiationPrep" },
  { value: "post_contract_review", labelKey: "auth.usagePurpose.postContractReview" },
  { value: "dispute_prep", labelKey: "auth.usagePurpose.disputePrep" },
  { value: "dispute_response", labelKey: "auth.usagePurpose.disputeResponse" },
] as const;

export type UsagePurpose = (typeof USAGE_PURPOSE_OPTIONS)[number]["value"];

export type SignupProfile = {
  fullName: string;
  phone: string;
  companyName: string;
  jobTitle: string;
  address: string;
  usagePurposes: UsagePurpose[];
  otherRequests: string;
};

export type UserProfile = {
  id: string;
  email: string | null;
  full_name: string | null;
  phone: string | null;
  company_name: string | null;
  job_title: string | null;
  address: string | null;
  usage_purposes: string[] | null;
  other_requests: string | null;
};

export function isProfileComplete(profile: UserProfile | null | undefined): boolean {
  if (!profile) return false;
  return Boolean(
    profile.full_name?.trim() &&
      profile.phone?.trim() &&
      profile.company_name?.trim() &&
      profile.job_title?.trim() &&
      profile.address?.trim() &&
      Array.isArray(profile.usage_purposes) &&
      profile.usage_purposes.length > 0,
  );
}
