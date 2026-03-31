/**
 * Content niches for AI-powered Reels generation.
 *
 * Ranked by: engagement potential x AI-generation suitability x save/share rate.
 * Data sourced from SocialInsider 2026, Buffer Algorithm Guide, Napolify, Zebracat,
 * Teleprompter.com, and MemberSpace research (2025-2026).
 */

export interface ReelNiche {
  id: string;
  /** Display name in Portuguese */
  label: string;
  /** English label for LLM prompts */
  labelEn: string;
  /** Short description for UI */
  description: string;
  /** Why this niche performs well (for tooltip/info) */
  whyItWorks: string;
  /** Tier: 1 = maximum engagement, 2 = high, 3 = moderate, 4 = faith & spirituality */
  tier: 1 | 2 | 3 | 4;
  /** Icon identifier (lucide icon name) */
  icon: string;
  /** Sub-themes the AI can explore */
  subThemes: string[];
  /** Hook templates (PT-BR) for script generation */
  hookTemplates: string[];
  /** CTA templates (PT-BR) */
  ctaTemplates: string[];
  /** Ideal video structure description for the LLM */
  videoStructure: string;
  /** Best content formats */
  formats: string[];
}

export const REEL_NICHES: ReelNiche[] = [
  // ── TIER 1: Maximum Engagement + Perfect AI Fit ──────────────────
  {
    id: "personal-finance",
    label: "Financas Pessoais",
    labelEn: "Personal Finance & Money Education",
    description: "Dicas de investimento, economia e educacao financeira",
    whyItWorks: "+200% saves vs media. CPM mais alto do Instagram. Publico salva compulsivamente.",
    tier: 1,
    icon: "DollarSign",
    subThemes: [
      "investimentos para iniciantes", "como sair das dividas", "sistemas de orcamento",
      "renda extra", "psicologia do dinheiro", "juros compostos", "mentalidade financeira",
      "independencia financeira", "armadilhas financeiras", "habitos de pessoas ricas",
    ],
    hookTemplates: [
      "Voce esta economizando errado. Deixa eu te mostrar por que.",
      "5 habitos financeiros que mudaram minha vida em 1 ano",
      "Se voce ganha menos de R$5mil, precisa saber disso",
      "O maior erro financeiro que 90% das pessoas cometem",
    ],
    ctaTemplates: [
      "Salva esse video antes de tomar sua proxima decisao financeira",
      "Compartilha com alguem que precisa organizar as financas",
      "Comenta qual dica voce vai aplicar primeiro",
    ],
    videoStructure: "Hook with shocking financial stat or counterintuitive claim (0-3s) -> 3-5 rapid financial tips with text overlays (3-40s) -> Strong CTA for saves (last 5s)",
    formats: ["lista de dicas", "mito vs verdade", "antes e depois financeiro", "habitos"],
  },
  {
    id: "self-improvement",
    label: "Desenvolvimento Pessoal",
    labelEn: "Self-Improvement & Personal Development",
    description: "Habitos, disciplina, rotinas e crescimento pessoal",
    whyItWorks: "+180% saves. 94% dos millennials investem em auto-melhoria. Cria lealdade emocional.",
    tier: 1,
    icon: "TrendingUp",
    subThemes: [
      "disciplina", "foco", "habit stacking", "mudanca de identidade",
      "journaling", "rotina matinal", "rotina noturna", "sistemas de produtividade",
      "proposito de vida", "autoconhecimento", "resiliencia",
    ],
    hookTemplates: [
      "3 habitos de pessoas altamente produtivas que ninguem te conta",
      "Se voce sente que esta estagnado, assista ate o final",
      "O segredo da disciplina nao e motivacao. E isso aqui.",
      "Para de fazer isso se voce quer evoluir de verdade",
    ],
    ctaTemplates: [
      "Comenta qual habito voce vai implementar hoje",
      "Salva pra relembrar quando precisar de motivacao",
      "Manda pra alguem que precisa ouvir isso",
    ],
    videoStructure: "Hook with relatable failure or pain point (0-3s) -> Reframe with principle (3-10s) -> 3 actionable steps with examples (10-40s) -> CTA for engagement (last 5s)",
    formats: ["habitos", "reframe mental", "rotina", "antes e depois pessoal"],
  },
  {
    id: "stoicism-mindset",
    label: "Mentalidade e Estoicismo",
    labelEn: "Mindset & Stoicism / Philosophy",
    description: "Filosofia pratica, sabedoria antiga aplicada ao dia a dia",
    whyItWorks: "Contas faceless atingem 900K+ seguidores. Burnout cultural criou demanda por sabedoria atemporal.",
    tier: 1,
    icon: "Brain",
    subThemes: [
      "Marco Aurelio", "Epiteto", "Seneca", "pratica diaria",
      "journaling estoico", "lidar com adversidade", "foco no que voce controla",
      "desapego", "tranquilidade interior", "virtude como objetivo",
    ],
    hookTemplates: [
      "Marco Aurelio escreveu isso ha 2000 anos e ainda e a melhor licao de vida",
      "O que os estoicos fariam sobre a ansiedade moderna",
      "Uma frase que mudou minha perspectiva para sempre",
      "Se voce se preocupa demais com o que os outros pensam, assista isso",
    ],
    ctaTemplates: [
      "Salva pra relembrar quando precisar",
      "Qual principio estoico mais te impactou? Comenta",
      "Compartilha com alguem que precisa dessa sabedoria",
    ],
    videoStructure: "Hook with a modern problem everyone faces (0-3s) -> Ancient principle that addresses it (3-15s) -> How to apply it today with examples (15-40s) -> CTA for saves (last 5s)",
    formats: ["citacao + aplicacao", "principio estoico moderno", "desafio diario", "reflexao"],
  },
  {
    id: "mental-health",
    label: "Saude Mental e Psicologia",
    labelEn: "Mental Health & Psychology",
    description: "Tecnicas de bem-estar, inteligencia emocional e autoconhecimento",
    whyItWorks: "+210% saves em conteudo acionavel. Alta de 52% em popularidade em 12 meses.",
    tier: 1,
    icon: "Heart",
    subThemes: [
      "ansiedade", "teoria do apego", "limites saudaveis", "vieses cognitivos",
      "regulacao emocional", "burnout", "tecnicas de terapia", "neurociencia dos habitos",
      "autoestima", "inteligencia emocional",
    ],
    hookTemplates: [
      "Se voce faz isso, presta atencao: pode ser um sinal de ansiedade",
      "3 tecnicas que psicologos usam para controlar a ansiedade em 5 minutos",
      "Por que voce se sabota toda vez que esta prestes a evoluir",
      "O que seu estilo de apego diz sobre seus relacionamentos",
    ],
    ctaTemplates: [
      "Compartilha com quem precisa ver isso",
      "Salva pra praticar quando sentir ansiedade",
      "Comenta se voce se identificou",
    ],
    videoStructure: "Hook with 'if you do this, pay attention' pattern (0-3s) -> Explain the psychology behind it (3-15s) -> 3 practical tools/techniques (15-40s) -> CTA for shares (last 5s)",
    formats: ["sinais de X", "tecnica pratica", "explicacao psicologica", "mito vs ciencia"],
  },
  {
    id: "ai-tools",
    label: "Ferramentas de IA",
    labelEn: "AI Tools & Productivity Tech",
    description: "Tutoriais de IA, automacao e ferramentas digitais",
    whyItWorks: "+420% crescimento em volume de busca. Menos de 200 criadores no espaco. 5-10x mais engajamento.",
    tier: 1,
    icon: "Sparkles",
    subThemes: [
      "prompts ChatGPT", "Midjourney", "automacao de workflows", "IA para negocios",
      "escrita com IA", "video com IA", "n8n/Zapier", "IA para estudantes",
      "ferramentas gratuitas", "como usar IA no trabalho",
    ],
    hookTemplates: [
      "Voce ainda esta fazendo isso manualmente? Existe uma IA que faz em 10 segundos",
      "5 ferramentas de IA que vao mudar sua produtividade em 2025",
      "Como usar ChatGPT do jeito certo (a maioria usa errado)",
      "Essa IA gratuita faz o trabalho de 3 funcionarios",
    ],
    ctaTemplates: [
      "Salva pra testar depois",
      "Comenta qual ferramenta voce mais quer aprender",
      "Segue pra mais dicas de IA toda semana",
    ],
    videoStructure: "Hook with 'you are still doing X manually?' (0-3s) -> Show the AI tool solving it quickly (3-15s) -> Step-by-step walkthrough with captions (15-40s) -> CTA for saves (last 5s)",
    formats: ["tutorial rapido", "antes e depois", "top 5 ferramentas", "prompt secreto"],
  },
  // ── TIER 2: High Engagement + Strong AI Fit ──────────────────────
  {
    id: "habits-neuroscience",
    label: "Habitos e Neurociencia",
    labelEn: "Habits & Behavior Science",
    description: "Como habitos se formam, dopamina, mudanca de comportamento",
    whyItWorks: "Atomic Habits nunca saiu de moda. Ciencia comportamental gera alto save rate.",
    tier: 2,
    icon: "Zap",
    subThemes: [
      "detox de dopamina", "atomic habits aplicado", "habitos de sono",
      "habito de leitura", "vicio em redes sociais", "loop de habitos",
      "recompensa e motivacao", "neuroplasticidade",
    ],
    hookTemplates: [
      "Seu cerebro te engana todo dia. Veja como funciona.",
      "Por que voce nao consegue manter um habito (e como resolver)",
      "A ciencia por tras do vicio em celular em 45 segundos",
    ],
    ctaTemplates: [
      "Qual habito voce quer instalar? Comenta aqui",
      "Salva esse video e reveja daqui 30 dias",
    ],
    videoStructure: "Hook with surprising neuroscience fact (0-3s) -> Explain the brain mechanism (3-15s) -> Practical system to apply (15-40s) -> CTA (last 5s)",
    formats: ["explicacao cientifica", "sistema pratico", "desafio 30 dias", "mito vs ciencia"],
  },
  {
    id: "productivity",
    label: "Produtividade e Foco",
    labelEn: "Productivity & Deep Work",
    description: "Tecnicas de foco, gestao de tempo e trabalho profundo",
    whyItWorks: "Micro-influencers faturam $2-5K/mes. Publico de alta intencao que converte.",
    tier: 2,
    icon: "Target",
    subThemes: [
      "deep work", "pomodoro", "second brain", "minimalismo digital",
      "time blocking", "GTD", "Notion/Obsidian", "gestao de energia",
    ],
    hookTemplates: [
      "Por que voce se distrai mesmo querendo focar (e a solucao)",
      "O metodo que triplicou minha produtividade em 1 semana",
      "Para de fazer lista de tarefas. Faca isso no lugar.",
    ],
    ctaTemplates: [
      "Salva esse sistema pra testar amanha",
      "Comenta qual tecnica funcionou melhor pra voce",
    ],
    videoStructure: "Hook explaining why common approach fails (0-3s) -> Reveal the mechanism/problem (3-10s) -> Present the system that fixes it (10-40s) -> CTA (last 5s)",
    formats: ["sistema de produtividade", "tutorial de ferramenta", "rotina de foco", "hack rapido"],
  },
  {
    id: "health-longevity",
    label: "Saude e Longevidade",
    labelEn: "Health & Longevity (Evidence-Based)",
    description: "Protocolos de saude baseados em evidencia, biohacking acessivel",
    whyItWorks: "+52% em engajamento de wellness. Mercado global de $4.27T ate 2027.",
    tier: 2,
    icon: "Activity",
    subThemes: [
      "otimizacao de sono", "exposicao ao frio", "jejum intermitente",
      "saude intestinal", "luz solar", "exercicio zona 2", "suplementos baseados em evidencia",
      "longevidade", "cognicao e cerebro",
    ],
    hookTemplates: [
      "5 habitos de saude que a ciencia comprova (e voce pode comecar hoje)",
      "Voce esta dormindo errado. A ciencia mostra o que funciona.",
      "O habito de 5 minutos que melhora sua saude em 30 dias",
    ],
    ctaTemplates: [
      "Qual voce ja pratica? Comenta",
      "Salva pra implementar essa semana",
    ],
    videoStructure: "Hook with myth or shocking health stat (0-3s) -> Science-backed reframe (3-15s) -> 3 actionable protocols (15-40s) -> CTA (last 5s)",
    formats: ["protocolo baseado em ciencia", "mito vs evidencia", "habito diario", "antes e depois"],
  },
  {
    id: "career-growth",
    label: "Crescimento Profissional",
    labelEn: "Career & Professional Growth",
    description: "Negociacao, habilidades, personal branding e mercado de trabalho",
    whyItWorks: "Alto compartilhamento via DM. Gen Z e millennials ansiosos com carreira em era de IA.",
    tier: 2,
    icon: "Briefcase",
    subThemes: [
      "negociacao salarial", "LinkedIn", "trabalho remoto",
      "habilidades do futuro", "personal branding", "transicao de carreira",
      "entrevista de emprego", "lideranca",
    ],
    hookTemplates: [
      "Ninguem te conta isso na faculdade (mas deveria)",
      "Como negociar um aumento de salario (script pronto)",
      "3 habilidades que vao te diferenciar no mercado em 2025",
    ],
    ctaTemplates: [
      "Compartilha com alguem que precisa ouvir isso",
      "Comenta sua area de atuacao",
    ],
    videoStructure: "Hook with 'nobody tells you this' pattern (0-3s) -> Reveal the career insight (3-15s) -> 3 steps to apply (15-40s) -> CTA for shares (last 5s)",
    formats: ["script de negociacao", "habilidade pratica", "erro comum", "dica de carreira"],
  },
  {
    id: "relationships",
    label: "Relacionamentos",
    labelEn: "Relationships & Social Psychology",
    description: "Comunicacao, inteligencia emocional e dinamicas sociais",
    whyItWorks: "Uma das categorias mais compartilhadas via DM. Pessoas enviam para parceiros/amigos.",
    tier: 2,
    icon: "Users",
    subThemes: [
      "estilos de apego", "comunicacao assertiva", "limites saudaveis",
      "linguagens do amor", "inteligencia emocional", "padroes toxicos vs saudaveis",
      "amizades", "dinamicas familiares",
    ],
    hookTemplates: [
      "Se seu parceiro faz isso, presta atencao",
      "3 sinais de que voce precisa estabelecer limites",
      "O que seu estilo de apego diz sobre voce (e como melhorar)",
    ],
    ctaTemplates: [
      "Manda pra alguem que precisa ver isso",
      "Comenta se voce se identificou",
    ],
    videoStructure: "Hook with relatable relationship scenario (0-3s) -> Psychological explanation (3-15s) -> How to handle it practically (15-40s) -> CTA for DM shares (last 5s)",
    formats: ["sinais e red flags", "tecnica de comunicacao", "explicacao de apego", "melhoria pratica"],
  },
  // ── TIER 3: High Engagement, Moderate AI Fit ─────────────────────
  {
    id: "nutrition",
    label: "Nutricao e Alimentacao",
    labelEn: "Nutrition & Practical Dietetics",
    description: "Alimentacao saudavel, mitos nutricionais e receitas praticas",
    whyItWorks: "Comida e universal. Desmistificar dietas performa extremamente bem no Brasil.",
    tier: 3,
    icon: "Apple",
    subThemes: [
      "ciencia da perda de peso", "saude intestinal", "alimentacao anti-inflamatoria",
      "meal prep", "jejum intermitente", "suplementacao", "mitos alimentares",
    ],
    hookTemplates: [
      "Voce acha que isso e saudavel? A ciencia discorda.",
      "3 trocas simples que transformam sua alimentacao",
    ],
    ctaTemplates: ["Salva pra tentar na proxima refeicao", "Comenta sua duvida sobre nutricao"],
    videoStructure: "Hook with food myth (0-3s) -> Science-based facts (3-20s) -> Practical swaps/tips (20-40s) -> CTA (last 5s)",
    formats: ["mito vs verdade", "troca saudavel", "o que comer em X situacao"],
  },
  {
    id: "study-learning",
    label: "Estudos e Aprendizado",
    labelEn: "Study Skills & Learning Science",
    description: "Tecnicas de estudo, memoria e aprendizado acelerado",
    whyItWorks: "Publico brasileiro massivo (vestibular, concursos). Conteudo salvo obsessivamente antes de provas.",
    tier: 3,
    icon: "BookOpen",
    subThemes: [
      "repeticao espacada", "leitura rapida", "active recall", "tecnica feynman",
      "sistemas de notas", "gestao de tempo para estudantes", "mapas mentais",
    ],
    hookTemplates: [
      "Voce esta estudando errado. A ciencia mostra o metodo certo.",
      "Como memorizar qualquer coisa usando essa tecnica simples",
    ],
    ctaTemplates: ["Salva pra usar na proxima sessao de estudo", "Marca um amigo que precisa disso"],
    videoStructure: "Hook challenging common study methods (0-3s) -> Explain the science of learning (3-15s) -> Practical technique demonstration (15-40s) -> CTA (last 5s)",
    formats: ["tecnica de estudo", "hack de memoria", "sistema de organizacao"],
  },
  {
    id: "minimalism",
    label: "Minimalismo",
    labelEn: "Minimalism & Intentional Living",
    description: "Vida intencional, desapego e consumo consciente",
    whyItWorks: "Save rate de 8-12%. Top contas atingem 834K+ seguidores com baixa competicao.",
    tier: 3,
    icon: "Minus",
    subThemes: [
      "minimalismo digital", "capsule wardrobe", "minimalismo financeiro",
      "essencialismo", "slow living", "desapego emocional",
    ],
    hookTemplates: [
      "Joguei fora 80% das minhas coisas. Isso aconteceu.",
      "Minimalismo nao e sobre ter pouco. E sobre isso.",
    ],
    ctaTemplates: ["Salva como inspiracao", "Comenta o que voce desapegaria primeiro"],
    videoStructure: "Hook with transformation or counterintuitive insight (0-3s) -> Philosophy behind minimalism (3-15s) -> Practical steps to start (15-40s) -> CTA (last 5s)",
    formats: ["desafio de desapego", "antes e depois", "filosofia aplicada"],
  },
  {
    id: "spirituality",
    label: "Espiritualidade e Paz Interior",
    labelEn: "Spirituality & Inner Peace",
    description: "Meditacao, gratidao, proposito e praticas contemplativas",
    whyItWorks: "Cultura brasileira tem forte conexao espiritual. Conteudo de meditacao e journaling engaja muito.",
    tier: 3,
    icon: "Sun",
    subThemes: [
      "meditacao", "pratica de gratidao", "journaling", "proposito/ikigai",
      "mindfulness", "energia pessoal", "rituais diarios",
    ],
    hookTemplates: [
      "Uma pratica de 5 minutos que transforma seu dia inteiro",
      "Se voce sente que esta perdido, assista isso ate o final",
    ],
    ctaTemplates: ["Salva pra praticar amanha de manha", "Comenta como voce cuida da sua paz interior"],
    videoStructure: "Hook inviting stillness or self-reflection (0-3s) -> Guided reflection or technique (3-30s) -> How to build a daily practice (30-40s) -> CTA (last 5s)",
    formats: ["pratica guiada", "reflexao diaria", "ritual matinal", "journaling prompt"],
  },
  {
    id: "entrepreneurship",
    label: "Empreendedorismo",
    labelEn: "Entrepreneurship & Business",
    description: "Negocios, marketing, vendas e mentalidade empreendedora",
    whyItWorks: "Brasil tem uma das maiores taxas de empreendedorismo do mundo. Publico com intencao de compra.",
    tier: 3,
    icon: "Rocket",
    subThemes: [
      "como comecar um negocio", "marketing digital", "precificacao",
      "aquisicao de clientes", "produtos digitais", "redes sociais para negocios",
    ],
    hookTemplates: [
      "Como essa pessoa faturou R$10mil em 30 dias (sem investir)",
      "O maior erro de quem esta comecando um negocio",
    ],
    ctaTemplates: ["Salva esse plano de acao", "Comenta sua ideia de negocio"],
    videoStructure: "Hook with case study or shocking result (0-3s) -> Explain the business model/strategy (3-20s) -> Step-by-step to replicate (20-40s) -> CTA (last 5s)",
    formats: ["caso de sucesso", "estrategia de negocio", "erro comum", "passo a passo"],
  },
  {
    id: "history-facts",
    label: "Historia e Curiosidades",
    labelEn: "History & Fascinating Facts",
    description: "Fatos historicos, curiosidades cientificas e conhecimento geral",
    whyItWorks: "Loop de curiosidade puro. 100% faceless-native. Hooks 'voce nao vai acreditar' funcionam muito.",
    tier: 3,
    icon: "Globe",
    subThemes: [
      "historia do Brasil", "historia mundial", "fatos cientificos",
      "experimentos psicologicos", "historia da economia", "curiosidades",
    ],
    hookTemplates: [
      "Voce nao vai acreditar no que aconteceu em [ano]",
      "3 fatos chocantes sobre [tema] que voce nao aprendeu na escola",
    ],
    ctaTemplates: ["Comenta qual fato te surpreendeu mais", "Salva pra compartilhar"],
    videoStructure: "Hook with shocking or counterintuitive fact (0-3s) -> Historical/scientific narrative (3-35s) -> Surprising conclusion (35-40s) -> CTA (last 5s)",
    formats: ["fatos chocantes", "historia em 45 segundos", "lado obscuro de X"],
  },
  // ── TIER 4: Faith & Spiritual Content ────────────────────────────
  {
    id: "bible-stories",
    label: "Historias Biblicas",
    labelEn: "Bible Stories & Biblical Wisdom",
    description: "Narrativas biblicas com licoes praticas para a vida moderna",
    whyItWorks: "Brasil tem 170M+ de cristaos. Conteudo biblico gera altissimo compartilhamento e saves. Formato narrativo prende atencao.",
    tier: 4,
    icon: "BookOpen",
    subThemes: [
      "parabolas de Jesus", "historias do Antigo Testamento", "Salmos e Proverbios",
      "vida de Moises", "vida de Davi", "vida de Jose do Egito",
      "milagres de Jesus", "Sermao da Montanha", "Apocalipse simplificado",
      "mulheres da Biblia", "profetas", "sabedoria de Salomao",
      "historias de fe e superacao", "a criacao", "Exodo e libertacao",
    ],
    hookTemplates: [
      "Essa historia biblica vai mudar sua perspectiva sobre sofrimento",
      "O que Davi fez quando tudo parecia perdido vai te surpreender",
      "Jesus contou essa parabola e mudou a vida de milhoes de pessoas",
      "A historia mais poderosa da Biblia que pouca gente conhece de verdade",
      "Se voce esta passando por dificuldade, essa passagem e pra voce",
    ],
    ctaTemplates: [
      "Compartilha com alguem que precisa dessa palavra hoje",
      "Salva pra ler de novo quando precisar de forca",
      "Comenta AMEM se essa mensagem tocou seu coracao",
      "Marca alguem que precisa ouvir isso",
    ],
    videoStructure: "Hook with emotional connection to modern struggle (0-3s) -> Set the biblical scene with vivid narration (3-15s) -> Tell the story with dramatic pacing (15-35s) -> Draw the lesson for today's life (35-42s) -> CTA for shares (last 3s)",
    formats: ["narrativa biblica", "licao de vida", "parabola explicada", "personagem biblico"],
  },
  {
    id: "catholic-prayers",
    label: "Oracoes Catolicas",
    labelEn: "Catholic Prayers & Devotions",
    description: "Oracoes, devocoes marianas, santos e espiritualidade catolica",
    whyItWorks: "Brasil e o maior pais catolico do mundo (120M+). Oracoes guiadas geram altissimo save rate. Conteudo de devocao e compartilhado em massa.",
    tier: 4,
    icon: "Heart",
    subThemes: [
      "Pai Nosso meditado", "Ave Maria", "Terco completo",
      "oracao da manha", "oracao da noite", "oracao de protecao",
      "devocao a Nossa Senhora", "Santos padroeiros", "oracao de cura",
      "Salmos para momentos dificeis", "novenas poderosas",
      "Santo Agostinho", "Sao Francisco de Assis", "Santa Teresa",
      "oracao do Anjo da Guarda", "oracao de gratidao",
    ],
    hookTemplates: [
      "Reze essa oracao poderosa antes de dormir hoje",
      "Nossa Senhora prometeu protecao a quem reza essa oracao todos os dias",
      "Se voce esta precisando de paz, pare tudo e reze comigo agora",
      "Essa oracao dos santos tem transformado vidas ha seculos",
      "Comece seu dia com essa oracao e sinta a diferenca",
    ],
    ctaTemplates: [
      "Salva pra rezar todos os dias",
      "Compartilha essa oracao com quem precisa de paz",
      "Comenta AMEM e receba essa bencao",
      "Marca alguem que precisa dessa oracao hoje",
    ],
    videoStructure: "Hook inviting prayer and stillness (0-3s) -> Context about the prayer/saint/devotion (3-10s) -> Guided prayer with reverent narration pace (10-38s) -> Blessing and CTA (last 5s)",
    formats: ["oracao guiada", "devocao mariana", "vida de santo", "salmo meditado", "novena"],
  },
  {
    id: "evangelical-prayers",
    label: "Oracoes Evangelicas",
    labelEn: "Evangelical Prayers & Worship",
    description: "Oracoes, devocoes, louvor e mensagens de fe evangelicas",
    whyItWorks: "Evangelicos sao 30%+ da populacao brasileira e crescendo. Conteudo de fe gera engajamento emocional intenso e compartilhamento viral.",
    tier: 4,
    icon: "Mic",
    subThemes: [
      "oracao de guerra espiritual", "oracao de madrugada", "oracao profética",
      "declaracoes de fe", "promessas biblicas", "oracao de libertacao",
      "louvor e adoracao", "oracao pelo financeiro", "oracao pela familia",
      "oracao de cura divina", "jejum e oracao", "oracao de gratidao",
      "mensagem profetica", "devocional diario", "testemunho de fe",
      "oracao de consagracao", "batalha espiritual",
    ],
    hookTemplates: [
      "Deus tem uma palavra poderosa pra sua vida hoje. Pare e ouca.",
      "Essa oracao de madrugada vai mudar sua semana. Ore comigo.",
      "Se voce esta enfrentando uma batalha, essa mensagem e pra voce",
      "Declare essas promessas sobre sua vida agora mesmo",
      "O Espirito Santo quer falar com voce atraves dessa oracao",
    ],
    ctaTemplates: [
      "Compartilha com alguem que precisa dessa palavra",
      "Comenta EU CREIO se voce recebe essa mensagem",
      "Salva pra orar de novo amanha de manha",
      "Marca alguem que esta precisando de uma oracao",
    ],
    videoStructure: "Hook with powerful declaration or divine invitation (0-3s) -> Set spiritual context with scripture reference (3-10s) -> Guided prayer with intensity and conviction (10-38s) -> Closing blessing and CTA (last 5s)",
    formats: ["oracao guiada", "declaracao profetica", "devocional", "promessa biblica", "louvor narrado"],
  },
];

/** Get niches by tier */
export function getNichesByTier(tier: 1 | 2 | 3 | 4): ReelNiche[] {
  return REEL_NICHES.filter(n => n.tier === tier);
}

/** Get a niche by ID */
export function getNicheById(id: string): ReelNiche | undefined {
  return REEL_NICHES.find(n => n.id === id);
}

/** Tier labels */
export const TIER_LABELS: Record<number, string> = {
  1: "Maximo Engajamento",
  2: "Alto Engajamento",
  3: "Engajamento Solido",
  4: "Fe e Espiritualidade",
};
