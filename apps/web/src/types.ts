export type Workspace = {
  id: string;
  name: string;
  description: string;
  role: string;
  created_at: string;
};
export type Session = {
  user: { id: string; name: string; email: string };
  workspaces: Workspace[];
};
export type Knowledge = {
  id: string;
  title: string;
  content: string;
  source: string;
  usage_scope: "marketing" | "internal";
  confirmed: boolean;
  kind: "fact" | "brand" | "material";
  file_id?: string;
  created_at: string;
};
export type Offering = {
  id: string;
  kind: "product" | "course";
  name: string;
  description: string;
  price: number;
  quantity: number;
  location: string;
  delivery: string;
  conversion_url: string;
  created_at: string;
};
export type Campaign = {
  id: string;
  name: string;
  objective: "sales" | "registration" | "awareness";
  audience: string;
  start_date: string;
  end_date: string;
  budget: number;
  channels: string[];
  offering_id?: string;
  notes: string;
  status: string;
  created_at: string;
};
export type Plan = {
  id: string;
  version: number;
  status: string;
  generation_mode: string;
  content: {
    theme: string;
    summary: string;
    audience: string;
    channels: { channel: string; reason: string; content_ideas: string[] }[];
    schedule: { day: string; action: string; channel: string }[];
    budget: { item: string; amount: number }[];
    warnings: string[];
    evidence: { id: string; title: string; source: string }[];
  };
  created_at: string;
};
export type Asset = {
  id: string;
  plan_id: string;
  campaign_id: string;
  version: number;
  channel: string;
  kind: string;
  title: string;
  body: string;
  content: Record<string, unknown>;
  status: string;
  checks: { level: string; message: string }[];
  generation_mode: string;
  created_at: string;
};
export type Publication = {
  id: string;
  campaign_id: string;
  plan_id: string;
  asset_id: string;
  channel: string;
  url: string;
  published_at: string;
};
export type Audit = {
  details?: Record<string, unknown>;
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  actor_name: string;
  created_at: string;
};
export type Metric = Record<string, string | number | null>;
export type Analytics = {
  stats: Record<string, number>;
  trends: {
    date: string;
    impressions: number;
    revenue: number;
    spend: number;
  }[];
  channels: {
    channel: string;
    impressions: number;
    interactions: number;
    orders: number;
    revenue: number;
    spend: number;
  }[];
  records: number;
};
export type Overview = {
  stats: Record<string, number>;
  trends: { date: string; impressions: number; revenue: number }[];
  recent_campaigns: Campaign[];
  activity: Audit[];
  connections: { ai_configured: boolean; publishing: string; checkout: string };
};
export type Review = {
  id: string;
  generation_mode: string;
  content: {
    facts: { statement: string; evidence: string }[];
    hypotheses: { statement: string; validation: string }[];
    suggestions: { action: string; metric: string }[];
    limitations: string[];
  };
  created_at: string;
};
export type Task = {
  id: string;
  kind: string;
  status: string;
  error?: string;
  generation_mode?: string;
  created_at: string;
};
