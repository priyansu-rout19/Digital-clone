"""
ParaGPT Corpus Seeder — Digital Clone Engine

Seeds sample documents and chunks for the ParaGPT (Parag Khanna) clone
so that citations show real-looking source titles and dates in the demo.

Inserts:
  - 16 documents with provenance JSONB (title, date, location)
  - 70+ document_chunks with real Gemini embeddings (1024-dim, truncated from 3072)

Idempotent: checks for existing rows before inserting.
Requires: GOOGLE_API_KEY and EMBEDDING_MODEL in .env

Run: python scripts/seed_paragpt_corpus.py
"""

import os
import sys
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Add project root to sys.path so core/ imports work
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import psycopg
from pgvector.psycopg import register_vector

from core.db.schema import Clone, Document
from core.db import psycopg_url
from core.rag.ingestion.embedder import get_embedder

# ---------------------------------------------------------------------------
# Database setup (same pattern as seed_db.py)
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://postgres@localhost/dce_dev")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# ---------------------------------------------------------------------------
# Sample corpus definition
# ---------------------------------------------------------------------------
# Each entry: (filename, source_type, mime_type, provenance_dict, list_of_passages)
#
# Passages are written in Parag Khanna's style: data-driven, framework-oriented,
# heavy on terms like "connectivity", "supply chains", "functional geography",
# "resilience". These are SAMPLE passages for demo, NOT real quotes.
# ---------------------------------------------------------------------------

CORPUS = [
    {
        "filename": "the_future_is_asian.pdf",
        "source_type": "book",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "The Future Is Asian",
            "date": "2019",
            "location": "Singapore",
        },
        "passages": [
            (
                "Asia's share of global GDP has surpassed 40 percent, and its intra-regional "
                "trade now exceeds its trade with the West. This is not a projection — it is "
                "the baseline from which the next phase of connectivity-driven growth will "
                "compound. Supply chains are re-anchoring across the Indo-Pacific corridor, "
                "and the center of economic gravity has shifted irreversibly eastward."
            ),
            (
                "ASEAN's combined economy ranks as the world's fifth largest, yet most Western "
                "analysts still treat it as a fragmented periphery. In reality, the ten member "
                "states are building a functional geography of shared infrastructure — high-speed "
                "rail, digital payments, harmonized customs — that makes their integration more "
                "tangible than the European Union's was at a comparable stage."
            ),
            (
                "Urbanization across Asia is creating megacity clusters that function as "
                "autonomous economic zones. From the Pearl River Delta to the Jakarta-Bandung "
                "corridor, these urban agglomerations generate more GDP than most nation-states. "
                "Connectivity between them — not national borders — defines the real map of "
                "21st-century commerce."
            ),
            (
                "Infrastructure investment in Asia has exceeded one trillion dollars annually, "
                "dwarfing comparable spending in any other region. Roads, ports, fiber-optic "
                "cables, and energy grids are the connective tissue of a continent that is "
                "building its future in concrete and silicon, not just policy declarations."
            ),
            (
                "The future of ASEAN lies in its ability to deepen intra-regional connectivity "
                "faster than external powers can fragment it. High-speed rail linking Kunming to "
                "Singapore, cross-border digital payment systems, and harmonized customs protocols "
                "are transforming ten separate markets into a single functional economic zone."
            ),
            (
                "India's rise as a manufacturing alternative to China is the most significant "
                "supply chain shift of the 2020s. But India's success depends on connectivity — "
                "port infrastructure, logistics efficiency, and digital integration with ASEAN "
                "markets. Geography alone guarantees nothing; infrastructure determines destiny."
            ),
            (
                "The Asian century is not about any single country's dominance — it is about "
                "the density of connections between Asian economies. Intra-Asian trade, investment, "
                "and migration flows now exceed Asia's exchanges with any other region. This "
                "self-reinforcing network effect is what makes Asia's rise structural, not cyclical."
            ),
        ],
    },
    {
        "filename": "connectography.pdf",
        "source_type": "book",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "Connectography",
            "date": "2016",
            "location": "Washington, D.C.",
        },
        "passages": [
            (
                "Supply chains have become the most accurate map of global power. Whoever "
                "controls the flow of goods, data, capital, and talent across borders wields "
                "more influence than whoever draws the borders themselves. Functional geography "
                "— the geography of infrastructure and connectivity — is replacing political "
                "geography as the organizing principle of the world system."
            ),
            (
                "The global infrastructure network now comprises over 64 million kilometers of "
                "highways, 2 million kilometers of pipelines, and 1.2 million kilometers of "
                "undersea cables. These are not just conduits — they are the arteries of a "
                "planetary organism whose resilience depends on redundancy and diversification "
                "rather than centralized control."
            ),
            (
                "Megacities are the nodes of the new connectivity map. With over 40 cities now "
                "exceeding 10 million people, the urban network generates 80 percent of global "
                "GDP. The competition for relevance is no longer between nations but between "
                "city-hubs that offer the densest intersection of talent, capital, and logistics."
            ),
            (
                "Borders still exist on political maps, but supply chains treat them as friction "
                "to be minimized. Every new trade corridor, every fiber-optic cable, every "
                "free-trade zone erodes the relevance of sovereignty defined by territorial "
                "lines. The world is moving from a map of divisions to a map of connections."
            ),
            (
                "Infrastructure is destiny. The civilizations that invested in roads, canals, "
                "and ports dominated their eras. Today, the same logic applies at planetary "
                "scale — nations that build connectivity infrastructure gain resilience, while "
                "those that rely on geographic isolation risk irrelevance."
            ),
            (
                "My framework for understanding global connectivity rests on three pillars: "
                "physical infrastructure (roads, ports, pipelines), digital infrastructure "
                "(fiber-optic cables, data centers, cloud platforms), and institutional "
                "infrastructure (trade agreements, customs unions, regulatory harmonization). "
                "Nations that invest across all three pillars gain compounding advantages."
            ),
            (
                "The map of the future is not defined by political borders but by supply chain "
                "corridors and infrastructure networks. I call this connectography — the mapping "
                "of how goods, data, capital, energy, and people flow across the world. This "
                "functional geography is a more accurate representation of global power than "
                "any political atlas."
            ),
        ],
    },
    {
        "filename": "move.pdf",
        "source_type": "book",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "MOVE",
            "date": "2021",
            "location": "Singapore",
        },
        "passages": [
            (
                "Climate migration is no longer a hypothetical — it is the defining demographic "
                "force of the 21st century. By 2050, an estimated 1.5 billion people will be "
                "displaced by rising seas, extreme heat, and water scarcity. The question is "
                "not whether mass movement will happen, but whether receiving regions will build "
                "the connectivity infrastructure to absorb it productively."
            ),
            (
                "Demographic imbalances are reshaping the global labor map. Aging societies in "
                "Europe and East Asia face worker shortages that only migration can solve, while "
                "young populations in South Asia and Africa seek opportunity. The supply and "
                "demand of human capital is the most consequential supply chain of all."
            ),
            (
                "Remote work has decoupled talent from geography for the first time in history. "
                "Knowledge workers now choose cities based on livability — climate resilience, "
                "digital infrastructure, cost of living — rather than proximity to headquarters. "
                "This functional migration is creating a new map of desirable geographies."
            ),
            (
                "The cities that will thrive in the next century are those investing in climate "
                "adaptation and digital connectivity simultaneously. Livability is the new "
                "competitiveness metric: clean water, reliable energy, fast internet, and "
                "resilient housing are the four pillars of the 21st-century urban contract."
            ),
        ],
    },
    {
        "filename": "how_to_run_the_world.pdf",
        "source_type": "book",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "How to Run the World",
            "date": "2011",
            "location": "New York",
        },
        "passages": [
            (
                "Traditional diplomacy — the exchange of ambassadors, the signing of treaties "
                "— is being supplemented and sometimes replaced by multi-stakeholder governance. "
                "Corporations, NGOs, philanthropies, and city mayors now participate directly in "
                "shaping global outcomes, from pandemic response to climate finance."
            ),
            (
                "Global governance in the 21st century requires a pragmatic, results-oriented "
                "approach that transcends ideological divides. The institutions built after "
                "World War II — the UN, IMF, World Bank — remain relevant only insofar as "
                "they adapt to a polycentric world where no single power dictates terms."
            ),
            (
                "The most effective form of international cooperation today is functional "
                "coalition-building around specific problems: vaccine distribution, supply chain "
                "resilience, digital standards. These coalitions of the willing achieve more in "
                "months than traditional multilateral negotiations do in decades."
            ),
        ],
    },
    {
        "filename": "cnn_asean_interview_2023.txt",
        "source_type": "interview",
        "mime_type": "text/plain",
        "provenance": {
            "title": "CNN Interview on ASEAN",
            "date": "2023-06-15",
            "location": "Singapore",
            "event": "CNN Asia Special",
        },
        "passages": [
            (
                "ASEAN centrality is not a diplomatic talking point — it is a structural reality. "
                "The bloc sits at the geographic crossroads of the Indo-Pacific, and every major "
                "power needs access to its markets, shipping lanes, and manufacturing capacity. "
                "US-China competition actually reinforces ASEAN's leverage rather than diminishing it."
            ),
            (
                "The US-China rivalry is reshaping trade corridors across Southeast Asia. "
                "Companies diversifying away from China are not leaving Asia — they are "
                "redistributing across Vietnam, Indonesia, Thailand, and Malaysia. This is "
                "supply chain rebalancing, not decoupling, and it strengthens the ASEAN "
                "ecosystem as a whole."
            ),
            (
                "ASEAN's greatest advantage is its pragmatism. Unlike the EU, which prioritizes "
                "regulatory harmonization, ASEAN focuses on building physical and digital "
                "connectivity first. The infrastructure comes before the institutions, and the "
                "economic integration follows the supply chains — not the other way around."
            ),
            (
                "The future of ASEAN is as the world's most consequential swing region. It is "
                "not aligned with either the US or China, and it does not need to be. ASEAN's "
                "strategy is to maximize connectivity with all major powers simultaneously — "
                "attracting investment from each while avoiding dependence on any single one."
            ),
            (
                "ASEAN's digital economy is projected to exceed 300 billion dollars by 2025. "
                "E-commerce platforms, fintech startups, and digital logistics companies are "
                "scaling across borders faster than physical infrastructure can keep up. This "
                "digital-first integration is ASEAN's greatest competitive advantage over older "
                "regional blocs that started with bureaucratic harmonization."
            ),
        ],
    },
    {
        "filename": "age_of_connectivity_essay.pdf",
        "source_type": "essay",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "The Age of Connectivity",
            "date": "2020-03-10",
        },
        "passages": [
            (
                "Digital infrastructure is the foundation of 21st-century resilience. Nations "
                "that invested in fiber-optic networks, cloud platforms, and digital payment "
                "systems before 2020 weathered the pandemic with minimal economic disruption. "
                "Connectivity is no longer a luxury — it is the baseline of national competence."
            ),
            (
                "The pandemic revealed that global networks are fragile but indispensable. "
                "The solution is not to retreat into autarky — which history shows always fails "
                "— but to build redundancy into supply chains, diversify supplier relationships, "
                "and invest in the digital layer that enables coordination without physical "
                "proximity."
            ),
            (
                "In a post-pandemic world, the divide between connected and disconnected "
                "societies will widen into the most consequential inequality of our era. "
                "Countries that build digital bridges — e-governance, telemedicine, remote "
                "education platforms — will compound their advantages, while those that "
                "remain analog will fall further behind."
            ),
        ],
    },
    {
        "filename": "wef_asia_panel_2024.txt",
        "source_type": "transcript",
        "mime_type": "text/plain",
        "provenance": {
            "title": "WEF Panel: Asia's Next Chapter",
            "date": "2024-01-18",
            "location": "Davos, Switzerland",
            "event": "World Economic Forum 2024",
        },
        "passages": [
            (
                "When people ask me about the future of ASEAN, I tell them to look at the "
                "infrastructure pipelines, not the diplomatic communiques. Three trillion dollars "
                "of planned infrastructure investment across Southeast Asia over the next decade "
                "will physically rewire the region. That is the future of ASEAN — concrete, "
                "steel, fiber optics, and energy grids connecting 700 million people."
            ),
            (
                "The Belt and Road Initiative accelerated Asia's connectivity, but ASEAN nations "
                "are not passive recipients. They are actively diversifying their infrastructure "
                "partnerships — Japan, Korea, India, the EU, and the US are all competing to "
                "finance projects. This multi-sourced connectivity model gives ASEAN more leverage "
                "and resilience than dependence on any single partner."
            ),
            (
                "Global supply chains are not deglobalizing — they are reglobalizing. The shift "
                "is from concentrated production in China to distributed manufacturing across "
                "ASEAN, India, and Mexico. This is not decoupling but diversification, and it "
                "represents the largest reorganization of global production since the 1990s."
            ),
            (
                "The geopolitics of AI will be defined not by who builds the best models but by "
                "who controls the data infrastructure and energy supply to run them. Asia is "
                "investing more in data centers and clean energy than any other region. The AI "
                "race is ultimately an infrastructure race, and infrastructure is what Asia does."
            ),
        ],
    },
    {
        "filename": "supply_chain_resilience_lecture.pdf",
        "source_type": "essay",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "Supply Chain Resilience in the Poly-Crisis Era",
            "date": "2023-09-20",
            "location": "Singapore",
        },
        "passages": [
            (
                "Resilience is not about self-sufficiency — it is about diversified connectivity. "
                "Nations that try to produce everything domestically will be outcompeted by those "
                "that maintain multiple supplier relationships across geographies. The goal is "
                "not fewer connections but more redundant ones."
            ),
            (
                "Southeast Asia's supply chain advantage is its geographic position between the "
                "Indian Ocean and the Pacific, combined with young demographics and improving "
                "infrastructure. Vietnam, Indonesia, and Thailand are the primary beneficiaries "
                "of the China-plus-one strategy, absorbing manufacturing that needs proximity "
                "to both Chinese inputs and Western markets."
            ),
            (
                "The semiconductor supply chain is the most consequential connectivity challenge "
                "of our era. Taiwan produces over 60 percent of the world's advanced chips, "
                "creating a single point of failure that threatens every industry. Diversifying "
                "chip production to the US, Japan, and Southeast Asia is not just economic policy "
                "— it is a matter of civilizational resilience."
            ),
            (
                "My framework for supply chain resilience has four dimensions: geographic "
                "diversification (multiple production sites), modal diversification (air, sea, "
                "rail, digital), temporal diversification (buffer stocks and just-in-case "
                "inventory), and relational diversification (multiple suppliers for critical "
                "inputs). Companies and nations that optimize across all four dimensions will "
                "thrive in an age of perpetual disruption."
            ),
        ],
    },
    # -----------------------------------------------------------------------
    # New documents added in Session 39 (corpus expansion)
    # -----------------------------------------------------------------------
    {
        "filename": "india_china_dynamics_lecture.pdf",
        "source_type": "lecture",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "India-China: Competition, Coexistence, Connectivity",
            "date": "2024-03-15",
            "location": "New Delhi, India",
            "event": "Raisina Dialogue 2024",
        },
        "passages": [
            (
                "India and China together represent 2.8 billion people and over 20 percent of "
                "global GDP. Their relationship will define the 21st century more than any other "
                "bilateral dynamic. Yet framing it purely as rivalry misses the complexity — "
                "trade between the two exceeded $135 billion in 2023 even as border tensions "
                "persisted. Connectivity and competition coexist."
            ),
            (
                "India's demographic dividend — 600 million people under 25 — is the counterpoint "
                "to China's aging population. But demographics alone determine nothing. India must "
                "convert its youth bulge into productive capacity through infrastructure investment, "
                "skills training, and manufacturing supply chains that connect to global demand."
            ),
            (
                "The China-plus-one strategy is not just about moving factories out of China. It "
                "is about building parallel supply chain ecosystems in India, Vietnam, and Indonesia "
                "that can operate independently when needed but remain connected to Chinese "
                "intermediate goods when not. Redundancy, not decoupling, is the rational approach."
            ),
            (
                "India's Digital Public Infrastructure — Aadhaar, UPI, ONDC — is a connectivity "
                "model that leapfrogs traditional development stages. Over a billion digital "
                "identities and 10 billion monthly UPI transactions demonstrate that digital "
                "infrastructure can democratize economic participation faster than physical "
                "infrastructure alone."
            ),
            (
                "The Himalayan border dispute between India and China is a 19th-century territorial "
                "conflict playing out alongside 21st-century economic integration. Both nations are "
                "pragmatic enough to manage this duality — hard power at the border, supply chains "
                "across the ocean. This is the new normal of great power relations in Asia."
            ),
        ],
    },
    {
        "filename": "ai_geopolitics_essay.pdf",
        "source_type": "essay",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "The Geopolitics of Artificial Intelligence",
            "date": "2024-06-10",
            "location": "Singapore",
        },
        "passages": [
            (
                "Artificial intelligence is the most consequential infrastructure investment of "
                "our generation. But unlike previous technology waves, AI's geopolitics is shaped "
                "by three physical constraints: semiconductor supply chains, data center energy "
                "consumption, and talent concentration. Whoever controls these three inputs "
                "controls the trajectory of AI development."
            ),
            (
                "The semiconductor supply chain is the most geographically concentrated critical "
                "infrastructure in human history. TSMC in Taiwan fabricates over 90 percent of "
                "the world's most advanced chips. This single point of failure represents a "
                "systemic risk that no amount of software innovation can mitigate — it requires "
                "physical diversification of fabrication capacity."
            ),
            (
                "AI governance cannot follow the 20th-century model of top-down regulation by "
                "nation-states. The technology moves faster than legislation, operates across "
                "borders by default, and is developed primarily by private actors. Effective AI "
                "governance requires multi-stakeholder coalitions that include technologists, "
                "ethicists, governments, and civil society — the same functional coalitions that "
                "work best for climate and pandemic response."
            ),
            (
                "Southeast Asia is emerging as an unexpected AI hub — not for foundational model "
                "training, but for AI deployment at scale. With 700 million people, rapid "
                "digitization, and pragmatic regulation, ASEAN offers the world's largest "
                "laboratory for AI applications in agriculture, fintech, healthcare, and "
                "logistics. The region that deploys AI most effectively may matter more than "
                "the one that develops the frontier models."
            ),
            (
                "Data sovereignty is the new resource nationalism. Countries are increasingly "
                "requiring that citizen data be stored and processed locally, fragmenting the "
                "global data ecosystem. This is creating a patchwork of data jurisdictions that "
                "mirrors the fragmentation of energy markets in the 20th century. Navigating "
                "these data borders is the new competency of globally connected enterprises."
            ),
        ],
    },
    {
        "filename": "middle_east_corridors.pdf",
        "source_type": "essay",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "The Middle East: From Oil Dependency to Connectivity Hub",
            "date": "2024-02-20",
            "location": "Dubai, UAE",
            "event": "World Government Summit 2024",
        },
        "passages": [
            (
                "The Gulf states are executing the most ambitious economic transformation in "
                "modern history — diversifying from hydrocarbon dependency to connectivity-based "
                "economies in a single generation. Dubai, Abu Dhabi, and Riyadh are investing "
                "hundreds of billions in logistics hubs, data centers, renewable energy, and "
                "financial infrastructure that position them as nodes connecting Asia, Africa, "
                "and Europe."
            ),
            (
                "The India-Middle East-Europe Economic Corridor (IMEC) represents a direct "
                "alternative to China's Belt and Road Initiative. By linking Indian ports to "
                "Gulf logistics hubs to Mediterranean shipping routes, IMEC creates a multi-modal "
                "corridor that reduces transit times by 40 percent compared to the Suez Canal "
                "route. This is functional geography in action — building alternatives that "
                "increase global supply chain resilience."
            ),
            (
                "Saudi Arabia's NEOM project is not just a city — it is a bet on connectivity "
                "as the post-oil economic engine. A linear city powered by renewable energy, "
                "connected by hyperloop, and governed by AI-driven systems represents the most "
                "radical reimagining of urban infrastructure since Brasilia. Whether it succeeds "
                "or not, it signals the direction of Gulf investment priorities."
            ),
            (
                "The Abraham Accords accelerated a connectivity revolution in the Middle East "
                "that was already underway. Israel-UAE-Bahrain economic integration — flights, "
                "trade, technology partnerships — demonstrates that functional economic interests "
                "can reshape geopolitical alignments faster than traditional peace processes. "
                "Commerce creates the facts on the ground that diplomacy formalizes later."
            ),
            (
                "The Red Sea corridor — from Suez to Bab el-Mandeb — carries 15 percent of "
                "global shipping. Houthi disruptions in 2024 exposed how a single chokepoint "
                "can cascade through global supply chains. The lesson: maritime connectivity "
                "requires diversification — overland corridors, alternative routes, and digital "
                "infrastructure that reduces dependence on physical shipping alone."
            ),
        ],
    },
    {
        "filename": "future_of_cities_talk.pdf",
        "source_type": "lecture",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "The Future of Cities: Climate, Connectivity, Competition",
            "date": "2024-09-05",
            "location": "London, UK",
            "event": "Chatham House Global Cities Forum",
        },
        "passages": [
            (
                "Cities are the operating system of the 21st century. Over 4.5 billion people "
                "now live in urban areas, and the 600 largest cities generate two-thirds of "
                "global GDP. National governments set policy, but cities deliver outcomes — "
                "infrastructure, services, livability, and economic opportunity. The competition "
                "for relevance is increasingly between cities, not countries."
            ),
            (
                "Climate adaptation is not optional for cities — it is existential. Sea-level "
                "rise threatens coastal megacities from Miami to Jakarta, while extreme heat "
                "makes Gulf and South Asian cities uninhabitable for parts of the year. The "
                "cities that invest in adaptation infrastructure — flood barriers, green "
                "corridors, cooling systems, resilient power grids — will attract talent and "
                "capital. Those that don't will experience managed retreat."
            ),
            (
                "The 15-minute city concept is a connectivity framework applied at urban scale. "
                "When residents can access work, education, healthcare, and leisure within a "
                "15-minute walk or bike ride, the city becomes a network of self-sufficient "
                "neighborhoods connected by public transit. This reduces car dependency, cuts "
                "emissions, and improves quality of life — all simultaneously."
            ),
            (
                "Smart cities are not about surveillance cameras and facial recognition — that "
                "is a dystopian caricature. Real smart city infrastructure means sensor networks "
                "that optimize traffic flow, AI-driven waste management, predictive maintenance "
                "of water systems, and digital twins that let planners simulate the impact of "
                "policy decisions before implementing them. Technology in service of livability."
            ),
            (
                "The global competition for talent is won by cities, not countries. A software "
                "engineer in Bangalore chooses between Singapore, Dubai, Berlin, and Toronto — "
                "not between India, UAE, Germany, and Canada. Cities compete on livability: "
                "housing affordability, internet speed, green space, healthcare access, cultural "
                "diversity, and safety. These are the new metrics of urban competitiveness."
            ),
        ],
    },
    {
        "filename": "climate_migration_podcast.txt",
        "source_type": "interview",
        "mime_type": "text/plain",
        "provenance": {
            "title": "Climate Migration and the New Geography of Opportunity",
            "date": "2024-04-22",
            "location": "Remote (podcast)",
            "event": "The Climate Question (BBC)",
        },
        "passages": [
            (
                "By 2050, climate migration will be the largest human movement since World War II. "
                "We are talking about 1.2 to 1.5 billion people displaced by rising seas, "
                "desertification, water scarcity, and extreme heat. This is not a distant "
                "projection — it is already happening. Bangladesh loses land to the sea every "
                "year, and Central American drought drives northward migration continuously."
            ),
            (
                "The question is not whether climate migration will happen but whether we will "
                "manage it as a crisis or as an opportunity. Countries with aging populations — "
                "Canada, Germany, Japan, Australia — need workers. Climate migrants need safety "
                "and opportunity. The connectivity between surplus labor and deficit labor is "
                "the most obvious win-win in global economics, yet political systems resist it."
            ),
            (
                "Climate-resilient geographies — the northern latitudes of Canada, Scandinavia, "
                "and Russia, plus highland regions globally — will become the most valuable "
                "real estate on Earth. This is not speculation; it is thermodynamics. As equatorial "
                "and coastal regions become less habitable, the functional geography of human "
                "settlement will shift dramatically northward and upward."
            ),
            (
                "Green infrastructure corridors — renewable energy networks, sustainable "
                "agriculture systems, climate-adapted housing — represent the next wave of "
                "connectivity investment. The trillion-dollar infrastructure boom in Asia is "
                "just the beginning. The next trillion will be invested in climate adaptation: "
                "flood barriers, desalination plants, heat-resistant urban design, and carbon "
                "capture networks."
            ),
            (
                "Migration and connectivity are inseparable. Every major wave of human migration "
                "in history — from the Silk Road to the Atlantic crossing — created new trade "
                "routes, cultural exchanges, and economic networks. Climate migration will do "
                "the same, creating unexpected connections between origin and destination "
                "communities. The remittance economy alone shows how migration generates "
                "persistent bilateral connectivity."
            ),
            (
                "Water scarcity is the under-reported driver of geopolitical instability. The "
                "Indus, Mekong, Nile, and Colorado rivers all serve populations whose water "
                "demands exceed sustainable supply. When water runs out, people move. Water "
                "infrastructure — desalination, recycling, efficient irrigation — is the most "
                "critical connectivity investment of the next two decades."
            ),
        ],
    },
    # -----------------------------------------------------------------------
    # New documents added in Session 47 (US-focused corpus expansion)
    # Fills gap: "What is your view on the US?" silenced due to missing content
    # -----------------------------------------------------------------------
    {
        "filename": "america_and_the_connected_world_order.pdf",
        "source_type": "essay",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "America and the Connected World Order",
            "date": "2024-05-12",
            "location": "Washington, DC",
        },
        "passages": [
            (
                "America's Partnership for Global Infrastructure and Investment (PGII) pledged "
                "$600 billion to counter China's Belt and Road, yet by 2024 actual disbursements "
                "remain a fraction of that figure. The US competes through alliances — mobilizing "
                "G7 capital, development finance institutions, and private sector co-investment — "
                "rather than unilateral state-driven buildout. This coalition model is slower but "
                "arguably more sustainable."
            ),
            (
                "The CHIPS and Science Act committed $52 billion to re-shore semiconductor "
                "fabrication, while the Inflation Reduction Act directed $370 billion toward "
                "clean energy manufacturing. Together they represent the largest US industrial "
                "policy commitment since the Interstate Highway System. The question is not "
                "whether America can spend, but whether it can build — permitting timelines and "
                "labor shortages remain the binding constraints."
            ),
            (
                "America's connectivity deficit is not about money — it is about execution. The "
                "US spends roughly $150 billion per year on infrastructure yet ranks 13th globally "
                "in infrastructure quality according to the World Economic Forum. China, by "
                "comparison, built 42,000 kilometers of high-speed rail while the US completed "
                "zero. The gap is institutional, not financial."
            ),
            (
                "The United States remains the world's premier hub for capital formation and "
                "talent attraction. Over 40 percent of Fortune 500 companies were founded or "
                "co-founded by immigrants or their children. Silicon Valley, Boston, and Austin "
                "function as global innovation nodes precisely because they sit at the intersection "
                "of connectivity-driven talent flows, venture capital, and research universities."
            ),
            (
                "America's global role in the connectivity era is best understood not as hegemon "
                "but as convener. The US anchors alliance networks — NATO, the Quad, AUKUS, "
                "IPEF — that collectively represent over 60 percent of global GDP. No other "
                "power can assemble coalitions of this scale. The question is not whether the US "
                "leads, but whether it leads through infrastructure investment or merely through "
                "security guarantees."
            ),
        ],
    },
    {
        "filename": "us_china_beyond_the_binary.pdf",
        "source_type": "lecture",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "US-China: Beyond the Binary",
            "date": "2024-07-08",
            "location": "Singapore",
            "event": "IISS Shangri-La Dialogue Side Event",
        },
        "passages": [
            (
                "The decoupling narrative is dramatically overstated. US-China bilateral trade "
                "exceeded $575 billion in 2023, and when intermediary flows through Vietnam, "
                "Mexico, and ASEAN are included, the real supply-chain entanglement is even "
                "deeper. We are witnessing selective tech bifurcation — chips, AI, quantum — "
                "layered on top of continued commercial interdependence in everything else."
            ),
            (
                "Reshoring and friendshoring sound compelling as slogans but the economics are "
                "sobering. Moving a single semiconductor fab costs $15-20 billion and takes five "
                "years. Replicating China's entire electronics assembly ecosystem across India, "
                "Vietnam, and Mexico would require trillions of dollars and decades. Supply-chain "
                "diversification is real; full decoupling is fantasy."
            ),
            (
                "The binary framing of US versus China obscures the agency of everyone else. "
                "ASEAN, India, the EU, the Gulf states, and Africa collectively represent over "
                "five billion people making independent connectivity decisions. They trade with "
                "both, invest with both, and align with neither exclusively. The world is not "
                "bifurcating — it is multi-aligning."
            ),
            (
                "Both the US and China shape global connectivity, but through fundamentally "
                "different models. China builds state-financed physical infrastructure — ports, "
                "rail, 5G networks — at scale and speed no democracy can match. The US exports "
                "financial architecture, technology platforms, and alliance frameworks. Neither "
                "model is sufficient alone; most countries pragmatically consume both."
            ),
            (
                "Technology bifurcation is creating two parallel innovation ecosystems for the "
                "first time since the Cold War. US export controls on advanced chips force China "
                "to build indigenous capacity in mature-node semiconductors, while American firms "
                "lose access to the world's largest electronics market. The cost of this "
                "bifurcation — estimated at $1-2 trillion in foregone trade over a decade — is "
                "borne by both sides and ultimately by consumers everywhere."
            ),
        ],
    },
    {
        "filename": "future_of_american_competitiveness.pdf",
        "source_type": "interview",
        "mime_type": "application/pdf",
        "provenance": {
            "title": "The Future of American Competitiveness",
            "date": "2024-10-15",
            "location": "New York",
            "event": "Bloomberg New Economy Forum",
        },
        "passages": [
            (
                "American domestic infrastructure tells a story of deferred maintenance and "
                "belated ambition. The American Society of Civil Engineers gives US infrastructure "
                "a C-minus grade — $4.6 trillion in needed repairs by 2030. The Bipartisan "
                "Infrastructure Law allocated $1.2 trillion, but execution has been hampered "
                "by permitting delays, labor shortages, and state-level coordination failures."
            ),
            (
                "Talent immigration is America's most underappreciated connectivity advantage. "
                "The US hosts over one million international students annually and attracts more "
                "high-skilled immigrants than any other nation. Over 55 percent of US unicorn "
                "startups have at least one immigrant founder. Restricting immigration is the "
                "single fastest way to erode American competitiveness."
            ),
            (
                "Silicon Valley functions as a global innovation node not because of any "
                "government program but because it sits at the densest intersection of venture "
                "capital, research universities, immigrant talent, and risk-tolerant culture on "
                "Earth. Replicating this ecosystem requires more than funding — it requires the "
                "connectivity-driven serendipity that only open, diverse talent hubs generate."
            ),
            (
                "Political polarization is America's most significant competitiveness risk. "
                "Long-term infrastructure investment requires bipartisan continuity — a bridge "
                "takes eight years from planning to completion, spanning multiple election cycles. "
                "When each administration reverses its predecessor's priorities, the result is "
                "perpetual restart rather than compounding progress. China's infrastructure "
                "advantage is fundamentally a continuity advantage."
            ),
            (
                "Comparing US, EU, and Chinese infrastructure strategies reveals three distinct "
                "models. China leads with state-directed speed — 42,000 km of high-speed rail in "
                "15 years. The EU prioritizes regulatory harmonization — slower but creating a "
                "single digital market of 450 million consumers. The US relies on private-sector "
                "innovation layered on aging public infrastructure. Each model has strengths, "
                "but the US approach is the most vulnerable to the gap between private dynamism "
                "and public decay."
            ),
        ],
    },
]


def _generate_embeddings() -> list[list[float]]:
    """Generate real Gemini embeddings for all corpus passages.

    Collects all passages into a single list and embeds them in batches
    via get_embedder() (Gemini gemini-embedding-001, 3072→1024 truncated).
    """
    all_passages = [p for entry in CORPUS for p in entry["passages"]]
    print(f"  Generating Gemini embeddings for {len(all_passages)} passages...")
    embedder = get_embedder()
    embeddings = embedder.embed(all_passages)
    print(f"  Got {len(embeddings)} embeddings ({len(embeddings[0])} dims each)")
    return embeddings


def seed_documents(db, clone_id: uuid.UUID) -> list[tuple[uuid.UUID, dict]]:
    """Insert Document rows via SQLAlchemy ORM. Returns list of (doc_id, entry)."""
    inserted = []

    for entry in CORPUS:
        # Idempotency: check by filename + clone_id
        existing = (
            db.query(Document)
            .filter(Document.clone_id == clone_id, Document.filename == entry["filename"])
            .first()
        )
        if existing:
            print(f"  Document '{entry['provenance']['title']}' already exists — skipping")
            inserted.append((existing.id, entry))
            continue

        doc = Document(
            id=uuid.uuid4(),
            clone_id=clone_id,
            filename=entry["filename"],
            source_type=entry["source_type"],
            mime_type=entry["mime_type"],
            file_path=f"/data/paragpt/{entry['filename']}",
            provenance=entry["provenance"],
            chunk_count=len(entry["passages"]),
            status="indexed",
        )
        db.add(doc)
        db.flush()  # Assign the id before we reference it for chunks
        inserted.append((doc.id, entry))
        print(f"  Inserted document: {entry['provenance']['title']} ({len(entry['passages'])} chunks)")

    db.commit()
    return inserted


def seed_chunks(
    doc_list: list[tuple[uuid.UUID, dict]],
    clone_id: uuid.UUID,
    embeddings: list[list[float]],
):
    """Insert document_chunks via raw psycopg + pgvector (same pattern as indexer.py).

    Uses ON CONFLICT (chunk_id) DO UPDATE for idempotency — safe to re-run.
    Includes search_vector (tsvector) for BM25 hybrid search.
    """
    raw_url = psycopg_url()
    if not raw_url:
        print("  ERROR: DATABASE_URL not set — cannot insert chunks")
        return

    total_inserted = 0
    emb_idx = 0  # Index into the flat embeddings list

    with psycopg.connect(raw_url) as conn:
        register_vector(conn)

        for doc_id, entry in doc_list:
            rows = []
            for i, passage in enumerate(entry["passages"]):
                chunk_id = f"{doc_id}_{i:04d}"
                embedding = embeddings[emb_idx]
                emb_idx += 1
                rows.append((
                    str(doc_id),
                    str(clone_id),
                    i,                          # chunk_index
                    chunk_id,                   # chunk_id
                    passage,                    # passage
                    entry["source_type"],       # source_type
                    "public",                   # access_tier
                    entry["provenance"].get("date"),  # date
                    embedding,                  # embedding (1024-dim vector)
                    passage,                    # repeated for to_tsvector('english', %s)
                ))

            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO document_chunks (
                        doc_id, clone_id, chunk_index, chunk_id, passage,
                        source_type, access_tier, date, embedding,
                        search_vector
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,
                        to_tsvector('english', %s))
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        passage = EXCLUDED.passage,
                        embedding = EXCLUDED.embedding,
                        search_vector = EXCLUDED.search_vector
                    """,
                    rows,
                )

            total_inserted += len(rows)

        conn.commit()

    print(f"  Inserted/updated {total_inserted} chunks across {len(doc_list)} documents")


def main():
    db = SessionLocal()
    try:
        print("=== ParaGPT Corpus Seeder ===\n")

        # Step 1: Find the paragpt-client clone
        print("1. Looking up paragpt-client clone...")
        clone = db.query(Clone).filter(Clone.slug == "paragpt-client").first()
        if not clone:
            print("  ERROR: Clone 'paragpt-client' not found.")
            print("  Run 'python scripts/seed_db.py' first to create clone profiles.")
            return
        print(f"  Found clone: {clone.slug} (id={clone.id})")

        # Step 2: Generate real Gemini embeddings
        print("\n2. Generating embeddings via Gemini API...")
        embeddings = _generate_embeddings()

        # Step 3: Insert documents via ORM
        print("\n3. Seeding documents...")
        doc_list = seed_documents(db, clone.id)

        # Step 4: Insert chunks via raw psycopg (pgvector)
        print("\n4. Seeding document chunks (with Gemini embeddings + tsvector)...")
        seed_chunks(doc_list, clone.id, embeddings)

        # Summary
        total_passages = sum(len(e["passages"]) for e in CORPUS)
        print(f"\nDone. Seeded {len(CORPUS)} documents with {total_passages} chunks (real Gemini embeddings).")

    finally:
        db.close()


if __name__ == "__main__":
    main()
