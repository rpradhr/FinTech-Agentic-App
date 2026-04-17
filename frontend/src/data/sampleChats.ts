export interface ChatMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  agentType?: "fraud" | "sentiment" | "loan" | "branch" | "advisory" | "supervisor";
  cards?: AgentCard[];
  timestamp: Date;
}

export interface AgentCard {
  type: "alert" | "metric" | "action" | "summary" | "evidence";
  title: string;
  value?: string;
  subtitle?: string;
  status?: string;
  items?: string[];
  color?: string;
}

// Pre-built sample conversation trees (indexed by prompt keyword)
export const SAMPLE_FLOWS: Record<string, ChatMessage[]> = {
  fraud: [
    {
      id: "u1", role: "user", content: "Show me the latest fraud alerts for customer C-ASHA001",
      timestamp: new Date(),
    },
    {
      id: "a1", role: "agent", content:
        "I found **2 active fraud alerts** for customer **Asha Mehta (C-ASHA001)**. " +
        "The most recent alert has a **critical risk score of 91%** — a $4,200 transaction via a new device at an unusual merchant. " +
        "Here's the breakdown:",
      agentType: "fraud",
      cards: [
        {
          type: "alert",
          title: "FRAUD-441 · Critical",
          value: "91% risk",
          subtitle: "$4,200.55 · MERCHANT_7781 · new device D-991",
          status: "pending_analyst_review",
          items: ["velocity_spike", "new_device", "merchant_cluster_match"],
          color: "#c5221f",
        },
        {
          type: "metric",
          title: "Prior pattern",
          value: "3 similar clusters",
          subtitle: "Same household H-001 involved in 3 prior alerts this quarter",
          color: "#ea4335",
        },
      ],
      timestamp: new Date(),
    },
  ],
  churn: [
    {
      id: "u2", role: "user", content: "Which customers are most at risk of churning this week?",
      timestamp: new Date(),
    },
    {
      id: "a2", role: "agent", content:
        "Based on recent interaction analyses, **3 customers** are in the **high churn-risk** tier (>65%) right now. " +
        "The primary drivers are fee disputes and unresolved complaint backlogs. " +
        "The Sentiment Agent flagged these signals in the last 48 hours:",
      agentType: "sentiment",
      cards: [
        {
          type: "metric",
          title: "Asha Mehta · C-ASHA001",
          value: "72% churn risk",
          subtitle: "Drivers: fee_dispute, long_wait_time",
          status: "very_negative",
          color: "#ea4335",
        },
        {
          type: "summary",
          title: "Cross-sell suppressed",
          subtitle: "Advisory agent has automatically suppressed cross-sell for high-risk customers until sentiment improves.",
          color: "#fbbc04",
        },
        {
          type: "action",
          title: "Recommended: Service recovery first",
          items: [
            "Schedule proactive outreach call within 24h",
            "Offer fee reversal as gesture of goodwill",
            "Assign dedicated relationship manager",
          ],
          color: "#1a73e8",
        },
      ],
      timestamp: new Date(),
    },
  ],
  loan: [
    {
      id: "u3", role: "user", content: "Summarize the loan review for application L-001",
      timestamp: new Date(),
    },
    {
      id: "a3", role: "agent", content:
        "Here's the **Loan Agent summary** for application **L-001** (Asha Mehta, personal loan, $25,000):",
      agentType: "loan",
      cards: [
        {
          type: "summary",
          title: "Application Overview",
          subtitle: "Personal loan · $25,000 · 60 months · Income: $120,000 · Credit: 720",
          status: "pending_documents",
          color: "#1a73e8",
        },
        {
          type: "evidence",
          title: "Missing Documents",
          items: ["bank_statement (3 months required)"],
          color: "#fbbc04",
        },
        {
          type: "alert",
          title: "Policy Note",
          subtitle: "Stated income-to-loan ratio is within policy bounds. No fraud flags on this customer's credit file.",
          value: "Low risk",
          color: "#34a853",
        },
        {
          type: "action",
          title: "AI Recommendation",
          subtitle: "Request bank statements. If received within 5 days and verified, recommend conditional approval.",
          color: "#1a73e8",
        },
      ],
      timestamp: new Date(),
    },
  ],
  branch: [
    {
      id: "u4", role: "user", content: "What's going on at the West Side branch?",
      timestamp: new Date(),
    },
    {
      id: "a4", role: "agent", content:
        "The Branch Monitor has flagged **3 anomalies** at **West Side (BR-WEST01)** over the last 7 days. " +
        "The most significant issue is a compound staffing-wait-time-complaint pattern:",
      agentType: "branch",
      cards: [
        {
          type: "alert",
          title: "Staffing Gap",
          value: "−2 FTEs vs. schedule",
          subtitle: "Actual staff: 8 vs. scheduled 10 (Mon–Wed pattern for 3 weeks)",
          status: "warning",
          color: "#fbbc04",
        },
        {
          type: "metric",
          title: "Wait Time Spike",
          value: "22.5 min avg",
          subtitle: "+40% above 14-day baseline of 16 min",
          color: "#ea4335",
        },
        {
          type: "action",
          title: "Probable Cause",
          items: [
            "Schedule compression following two staff leaves",
            "No temporary coverage arranged",
            "Complaint count increased from 3 to 9 in same window",
          ],
          color: "#5f6368",
        },
      ],
      timestamp: new Date(),
    },
  ],
  advice: [
    {
      id: "u5", role: "user", content: "Generate advice for customer C-ASHA001",
      timestamp: new Date(),
    },
    {
      id: "a5", role: "agent", content:
        "The Advisory Agent has generated a **draft recommendation pack** for Asha Mehta. " +
        "⚠️ Note: Cross-sell is **suppressed** due to elevated churn risk. Service recovery is prioritized.",
      agentType: "advisory",
      cards: [
        {
          type: "action",
          title: "1 · Service Recovery (Priority)",
          subtitle: "Address open fee dispute before any product conversations. Suggest a $35 fee waiver and personal follow-up.",
          items: ["Suggested script: 'Asha, I wanted to personally reach out about your recent experience…'"],
          color: "#ea4335",
        },
        {
          type: "action",
          title: "2 · Emergency Fund Gap",
          subtitle: "Customer has $12k monthly surplus but no dedicated emergency savings. High-yield savings product is a fit.",
          items: ["Savings gap: ~3 months living expenses", "Product fit: Premier Savings (2.8% APY)"],
          color: "#1a73e8",
        },
        {
          type: "metric",
          title: "Advisor must approve before delivery",
          subtitle: "No recommendation reaches the customer without your sign-off.",
          value: "HITL gate",
          color: "#5f6368",
        },
      ],
      timestamp: new Date(),
    },
  ],
};

export const SUGGESTED_PROMPTS = [
  { label: "Fraud alerts", prompt: "Show me the latest fraud alerts for customer C-ASHA001", icon: "🔍" },
  { label: "Churn risk",   prompt: "Which customers are most at risk of churning this week?",  icon: "📉" },
  { label: "Loan review",  prompt: "Summarize the loan review for application L-001",          icon: "📋" },
  { label: "Branch ops",   prompt: "What's going on at the West Side branch?",                 icon: "🏦" },
  { label: "Advisory",     prompt: "Generate advice for customer C-ASHA001",                   icon: "💡" },
];
