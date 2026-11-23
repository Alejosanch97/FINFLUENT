/* =====================================================================
   FINFLUENT · MAPA DE CURSOS
   Un grado = 4 periodos. Aquí vive lo que el Dashboard, el Home, el Admin
   y el diploma necesitan saber de cada grado. Para agregar un grado nuevo:
   1) agrégalo aquí  2) registra sus 4 componentes en PAGES (Dashboard.jsx).

   "key" es la llave con la que se guarda el progreso (igual que en el
   Excel original: sexto usa P1..P4, los demás 7P1, 8P2, 11P4…).
   ===================================================================== */
import {
  Coins, PiggyBank, Lightbulb, Globe, TrendingUp, Landmark, ClipboardList, Flag,
  Map, Target, CreditCard, Rocket, Building2, FlaskConical, Store, Paperclip,
  Calculator, LineChart, Compass, Hammer, Handshake, BarChart3, GraduationCap,
} from "lucide-react";

export const GRADES = ["6", "7", "8", "9", "10", "11"];

export const COURSES = {
  "6": {
    name: "Money Explorers",
    tagline: "From barter to your first company.",
    level: "A2",
    periods: [
      { key: "P1", n: 1, title: "From Barter to Money", short: "Barter to Money", Icon: Coins, question: "How did money change the way people exchange goods, and why is it important in our daily lives?" },
      { key: "P2", n: 2, title: "My First Financial Plan", short: "First Financial Plan", Icon: PiggyBank, question: "How can saving, budgeting, and responsible spending help us achieve our personal goals?" },
      { key: "P3", n: 3, title: "Young Entrepreneurs Lab", short: "Entrepreneurs Lab", Icon: Lightbulb, question: "How can I create a business idea that solves a real problem and helps my community?" },
      { key: "P4", n: 4, title: "My Company Goes Global", short: "Company Goes Global", Icon: Globe, question: "How can technology help my business grow — safely, honestly and around the world?" },
    ],
    canDo: [
      "explain how money replaced barter and the three jobs money does",
      "set a saving goal, build a first budget and pay safely with digital money",
      "turn a real problem of the community into a business idea",
      "take a small company online in a safe and honest way",
    ],
  },
  "7": {
    name: "Smart Consumers",
    tagline: "Prices, banks and a plan of your own.",
    level: "A2+",
    periods: [
      { key: "7P1", n: 1, title: "Why Do Prices Change?", short: "Why Prices Change", Icon: TrendingUp, question: "Why do prices change, and how can understanding inflation help us become smarter consumers?" },
      { key: "7P2", n: 2, title: "How Banks Work: Junior Financial Advisors", short: "How Banks Work", Icon: Landmark, question: "How can banks and responsible financial decisions help people achieve their goals?" },
      { key: "7P3", n: 3, title: "Smart Banking: My Personal Financial Plan", short: "Smart Banking", Icon: ClipboardList, question: "How can saving, banks and responsible credit help me achieve financial wellbeing?" },
      { key: "7P4", n: 4, title: "Building My Financial Future", short: "My Financial Future", Icon: Flag, question: "How can smart financial planning help us build a secure future?" },
    ],
    canDo: [
      "explain why prices change and how inflation affects everyday decisions",
      "describe how banks work and advise others on basic financial products",
      "use saving, banking and responsible credit inside a personal financial plan",
      "plan financial goals for the future and defend them with numbers",
    ],
  },
  "8": {
    name: "Money Architects",
    tagline: "Design the plan, then build the business.",
    level: "B1",
    periods: [
      { key: "8P1", n: 1, title: "My Money Blueprint", short: "Money Blueprint", Icon: Map, question: "How can a personal financial plan help us make smarter financial decisions?" },
      { key: "8P2", n: 2, title: "Saving Today, Achieving Tomorrow", short: "Saving Today", Icon: Target, question: "How can saving money today help us achieve bigger opportunities tomorrow?" },
      { key: "8P3", n: 3, title: "Banking, Credit & Investing", short: "Banking & Credit", Icon: CreditCard, question: "How can banks, saving strategies and responsible financial services help people achieve financial security?" },
      { key: "8P4", n: 4, title: "Startup Studio", short: "Startup Studio", Icon: Rocket, question: "How can a digital business receive money, protect its customers and create real value?" },
    ],
    canDo: [
      "design a personal financial plan with a realistic budget",
      "choose saving strategies, measure opportunity cost and plan an emergency fund",
      "compare banking, credit and first investment options and their real costs",
      "plan a digital business that receives payments and protects its customers",
    ],
  },
  "9": {
    name: "The District",
    tagline: "Four districts, one financial city.",
    periods: [
      { key: "9P1", n: 1, title: "The Financial District", short: "Financial District", Icon: Building2, question: "How can banking services, financial products and responsible decisions help young people build a secure financial future?" },
      { key: "9P2", n: 2, title: "The Product Lab", short: "Product Lab", Icon: FlaskConical, question: "How can we compare modern financial products, understand their costs and risks, and protect our money in a digital world?" },
      { key: "9P3", n: 3, title: "Startup District", short: "Startup District", Icon: Store, question: "How can we turn a real problem into a business that creates value, makes a profit and communicates honestly?" },
      { key: "9P4", n: 4, title: "Global District", short: "Global District", Icon: Globe, question: "How do the dollar, inflation, trade and sustainability change a business — and how can we create value for people and the planet?" },
    ],
    canDo: [
      "use banking services and financial products with responsible decisions",
      "compare modern financial products, their costs and risks, and protect money online",
      "turn a real problem into a business that creates value and makes a profit",
      "explain how the dollar, inflation, trade and sustainability change a business",
    ],
  },
  "10": {
    name: "Future Me",
    tagline: "The math of money and the life you want.",
    periods: [
      { key: "10P1", n: 1, title: "From Zero", short: "From Zero", Icon: Paperclip, question: "How can I create value from almost nothing — with negotiation, perceived value and the laws of the market?" },
      { key: "10P2", n: 2, title: "Money Math Lab", short: "Money Math Lab", Icon: Calculator, question: "Why is a peso today worth more than tomorrow — and how do I make math work for me, not against me?" },
      { key: "10P3", n: 3, title: "Global Investor", short: "Global Investor", Icon: LineChart, question: "How do I go from saver to investor — with controlled risk, protection from the dollar and zero scams?" },
      { key: "10P4", n: 4, title: "Future Me", short: "Future Me", Icon: Compass, question: "I know how money works. Now: who do I want to be — and how will I pay for that life?" },
    ],
    canDo: [
      "explain value, supply and demand, and pitch a brand built from zero",
      "apply financial mathematics: time value of money, simple and compound interest, effective rates and the real cost of a loan",
      "evaluate investments with risk and return, stocks and ETFs, NPV, IRR and payback",
      "connect personal strengths, career research and money into a life plan",
    ],
  },
  "11": {
    name: "Founder Year",
    tagline: "Build it, fund it, invest it, graduate.",
    periods: [
      { key: "11P1", n: 1, title: "Startup Studio: Build It", short: "Build It", Icon: Hammer, question: "Can your team turn a real problem into a physical product that people actually pay for?" },
      { key: "11P2", n: 2, title: "Shark Tank: Fund It & Value It", short: "Fund It & Value It", Icon: Handshake, question: "How much is your company really worth — and can you convince the sharks with your numbers?" },
      { key: "11P3", n: 3, title: "Investor Lab 18+ & Life Plan", short: "Investor Lab 18+", Icon: BarChart3, question: "What will you do with your money — and your future — the day you turn 18?" },
      { key: "11P4", n: 4, title: "Game Zone & Graduation", short: "Game Zone", Icon: GraduationCap, question: "How much do you really know — and how far did you come?" },
    ],
    canDo: [
      "design a product from customer discovery to unit economics and break-even",
      "read a P&L and cash flow, value a company and negotiate an investment deal",
      "build a long-term investing plan that beats inflation, and a personal life plan",
      "defend six years of financial learning in a final graduation showcase",
    ],
  },
};

export const courseOf = (grade) => COURSES[String(grade || "").trim()] || null;
export const periodKeysOf = (grade) => (courseOf(grade)?.periods || []).map((p) => p.key);
export const ordinal = (g) => ({ "6": "6th", "7": "7th", "8": "8th", "9": "9th", "10": "10th", "11": "11th" }[String(g)] || `${g}th`);
