export interface QuestionGroup {
  topic: string;
  icon: string;
  questions: string[];
}

export interface Domain {
  id: string;
  name: string;
  icon: string;
  description: string;
  schemes: string[];
  sampleQuestions: string[];
  questionGroups: QuestionGroup[];
}

export const DOMAINS: Domain[] = [
  {
    id: "healthcare",
    name: "Healthcare",
    icon: "🏥",
    description: "Ayushman Bharat PMJAY, hospital access, health cards",
    schemes: ["Ayushman Bharat (PMJAY)", "CGHS", "ESIC"],
    sampleQuestions: [
      "Who is eligible for Ayushman Bharat?",
      "How do I get a health card?",
      "Which hospitals accept PMJAY?",
    ],
    questionGroups: [
      {
        topic: "Eligibility & Registration",
        icon: "📋",
        questions: [
          "Who is eligible for Ayushman Bharat PMJAY?",
          "How do I check if my name is on the PMJAY list?",
          "What documents are needed to get a health card?",
        ],
      },
      {
        topic: "Benefits & Coverage",
        icon: "💊",
        questions: [
          "What treatments are covered under PMJAY?",
          "What is the maximum coverage amount per family?",
          "Are pre-existing diseases covered under Ayushman Bharat?",
          "Can I get cashless treatment at private hospitals?",
        ],
      },
      {
        topic: "Hospitals & Services",
        icon: "🏨",
        questions: [
          "How do I find the nearest PMJAY empanelled hospital?",
          "Which hospitals accept the Ayushman Bharat card?",
          "How do I get a health card printed?",
        ],
      },
      {
        topic: "CGHS & ESIC",
        icon: "🩺",
        questions: [
          "Who can use CGHS and how to enroll?",
          "What is ESIC and who is eligible for it?",
          "How to claim ESIC medical benefits?",
        ],
      },
    ],
  },
  {
    id: "agriculture",
    name: "Agriculture",
    icon: "🌾",
    description: "PM Kisan, crop insurance, farmer subsidies",
    schemes: ["PM Kisan Samman Nidhi", "PM Fasal Bima Yojana", "Kisan Credit Card"],
    sampleQuestions: [
      "When does PM Kisan installment come?",
      "How to register for PM Kisan?",
      "What is crop insurance process?",
    ],
    questionGroups: [
      {
        topic: "PM Kisan Samman Nidhi",
        icon: "💰",
        questions: [
          "When does the PM Kisan installment come?",
          "How do I register for PM Kisan?",
          "How to check my PM Kisan payment status?",
          "What is the total amount given under PM Kisan per year?",
        ],
      },
      {
        topic: "Crop Insurance",
        icon: "🌱",
        questions: [
          "How to apply for PM Fasal Bima Yojana?",
          "Which crops are covered under PMFBY?",
          "How do I file a crop damage claim?",
          "What is the premium amount for crop insurance?",
        ],
      },
      {
        topic: "Kisan Credit Card",
        icon: "💳",
        questions: [
          "How to get a Kisan Credit Card?",
          "What is the loan limit under KCC?",
          "What is the interest rate on a Kisan Credit Card?",
        ],
      },
    ],
  },
  {
    id: "education",
    name: "Education",
    icon: "🎓",
    description: "Scholarships, NSP portal, student loans",
    schemes: ["National Scholarship Portal", "Pre-Matric Scholarship", "Post-Matric Scholarship"],
    sampleQuestions: [
      "How to apply for scholarship?",
      "What documents are needed for NSP?",
      "What is the income limit for scholarship?",
    ],
    questionGroups: [
      {
        topic: "NSP Scholarships",
        icon: "📚",
        questions: [
          "How do I apply for a scholarship on the NSP portal?",
          "What is the income limit to get a scholarship?",
          "What is the last date to apply for scholarships?",
          "How do I check my scholarship application status?",
        ],
      },
      {
        topic: "Eligibility & Documents",
        icon: "📄",
        questions: [
          "What documents are needed for NSP registration?",
          "Can minority students apply for central scholarships?",
          "Are there scholarships specifically for girls?",
          "Can SC/ST students get extra scholarship benefits?",
        ],
      },
      {
        topic: "Student Loans",
        icon: "🏦",
        questions: [
          "How to apply for a student education loan?",
          "What is the Vidya Lakshmi portal?",
          "Is there interest subsidy on education loans?",
        ],
      },
    ],
  },
  {
    id: "housing",
    name: "Housing",
    icon: "🏠",
    description: "PM Awas Yojana, rural and urban housing schemes",
    schemes: ["PMAY Urban", "PMAY Gramin", "DAY-NULM"],
    sampleQuestions: [
      "How to apply for PM Awas Yojana?",
      "Who is eligible for free housing?",
      "What is the subsidy on home loan?",
    ],
    questionGroups: [
      {
        topic: "PMAY Urban",
        icon: "🏙️",
        questions: [
          "How do I apply for PMAY Urban?",
          "Who is eligible for PMAY urban housing?",
          "What is the home loan subsidy under PMAY?",
          "How do I check my PMAY application status?",
        ],
      },
      {
        topic: "PMAY Gramin",
        icon: "🏡",
        questions: [
          "How to apply for rural housing under PMAY Gramin?",
          "What is the benefit amount given under PMAY Gramin?",
          "Who approves and verifies PMAY Gramin applications?",
        ],
      },
      {
        topic: "Documents & Process",
        icon: "📝",
        questions: [
          "What documents are needed to apply for PMAY?",
          "How long does PMAY approval take?",
          "Can I check PMAY status using my Aadhaar number?",
        ],
      },
    ],
  },
  {
    id: "employment",
    name: "Employment",
    icon: "💼",
    description: "MGNREGA, skill development, job portal",
    schemes: ["MGNREGA", "PM Kaushal Vikas Yojana", "NCS Portal"],
    sampleQuestions: [
      "How to get MGNREGA job card?",
      "What is the daily wage under MGNREGA?",
      "How to register on NCS portal?",
    ],
    questionGroups: [
      {
        topic: "MGNREGA",
        icon: "⛏️",
        questions: [
          "How do I get an MGNREGA job card?",
          "What is the daily wage under MGNREGA?",
          "How do I demand work under MGNREGA?",
          "What happens if work is not provided within 15 days?",
        ],
      },
      {
        topic: "Skill Development",
        icon: "🛠️",
        questions: [
          "What courses are available under PM Kaushal Vikas Yojana?",
          "How do I enroll in a skill training centre?",
          "Is there a stipend during skill development training?",
          "Do I get a certificate after PMKVY training?",
        ],
      },
      {
        topic: "Job Portal (NCS)",
        icon: "💻",
        questions: [
          "How do I register on the NCS job portal?",
          "How to search for government jobs on NCS?",
          "Can I upload my resume on the NCS portal?",
        ],
      },
    ],
  },
  {
    id: "social_welfare",
    name: "Social Welfare",
    icon: "🤝",
    description: "Pension schemes, disability benefits, women welfare",
    schemes: ["NSAP Pension", "PM Ujjwala Yojana", "Beti Bachao Beti Padhao"],
    sampleQuestions: [
      "How to apply for old age pension?",
      "Who is eligible for widow pension?",
      "How to get free LPG connection?",
    ],
    questionGroups: [
      {
        topic: "Pension Schemes",
        icon: "👴",
        questions: [
          "How do I apply for old age pension?",
          "Who is eligible for widow pension?",
          "What is the monthly pension amount under NSAP?",
          "How to check pension payment status?",
        ],
      },
      {
        topic: "Women & Child Welfare",
        icon: "👩",
        questions: [
          "How to get a free LPG connection under PM Ujjwala?",
          "What schemes are available for pregnant women?",
          "How to apply for Beti Bachao Beti Padhao benefits?",
          "What is the Maternity Benefit under PMMVY?",
        ],
      },
      {
        topic: "Disability Benefits",
        icon: "♿",
        questions: [
          "What benefits are available for persons with disabilities?",
          "How do I get a disability certificate?",
          "Is there a monthly pension for disabled individuals?",
        ],
      },
    ],
  },
];

export const LANGUAGES = [
  { code: "en", label: "English",   nativeLabel: "English" },
  { code: "hi", label: "Hindi",     nativeLabel: "हिन्दी" },
  { code: "ta", label: "Tamil",     nativeLabel: "தமிழ்" },
  { code: "te", label: "Telugu",    nativeLabel: "తెలుగు" },
  { code: "mr", label: "Marathi",   nativeLabel: "मराठी" },
  { code: "bn", label: "Bengali",   nativeLabel: "বাংলা" },
  { code: "ml", label: "Malayalam", nativeLabel: "മലയാളം" },
  { code: "kn", label: "Kannada",   nativeLabel: "ಕನ್ನಡ" },
];
