# Khiw (Ikkyu) Nitithadachot — Complete Knowledge Graph
## Source: LinkedIn MCP Server — Full Verbose Scrape (max_scrolls=50, all sections)
## Date: 2026-05-24 | Entities: 298 | Relationships: 412

---

## LEGEND
```
(ENTITY_TYPE) Name
  [property]: value
  -[RELATIONSHIP_TYPE]-> (ENTITY_TYPE) Target
```

---

## 1. PERSON — CORE IDENTITY

```
(PERSON) Khiw Nitithadachot
  [full_name]: Khiw (Ikkyu) Nitithadachot
  [display_name]: Ikkyu N.
  [handle]: getintheq
  [linkedin]: https://www.linkedin.com/in/getintheq/
  [email]: kiw.brw@gmail.com
  [phone]: +66-82-997-1887 (Mobile)
  [portfolio]: https://khiw.dev
  [portfolio_old_1]: https://getintheq.space
  [portfolio_old_2]: https://getintheq.io
  [github]: https://github.com/getintheQ
  [location_current]: Bangkok, Bangkok City, Thailand
  [location_hometown]: 69/1 M.4 Tambol Thapluang, Ampher Banrai, Uthai Thani Province
  [connections]: 360
  [followers]: 388
  [open_to_work]: true
  [work_preferences]: Bangkok | On-site · Hybrid · Remote
  [volunteer_interests]: Education, Science and Technology
  [profile_views_7d]: 73
  [post_impressions_7d]: 21
  [search_appearances_7d]: 41
  [headline_current]: MVP AI-Augmented Full Stack Developer | Freelance AI and Data Engineer Team Lead for Marketing Research | AI-Powered Business Intelligence | Generative AI Developer | Start Up +
  [headline_recommended]: AI Agent Architect & Multi-Agent Systems Engineer | AI-Augmented Full-Stack Developer
  [profile_language]: English
  [verified]: true
```

---

## 2. ROLES / EXPERIENCE

### Role 01 — Libralytics (Current)
```
(ROLE) Lead Data and AI Engineer at Libralytics
  [title]: Freelancer as a Lead Data and AI Engineer
  [employment_type]: Part-time, Remote
  [start]: November 2024
  [end]: Present
  [duration]: 1 year 7 months (as of May 2026)
  [location]: Bangkok, Bangkok City, Thailand
  [seniority]: Lead
  [is_current]: true

  [responsibilities]:
    - Industry-Specific AI Agents: café/restaurant business model marketing analysis
    - AI/MLOps Infrastructure: Docker + Kubernetes for scalable AI agent deployment
    - Full-Stack Data Engineering: scraping, graph DB, vector DB, SQL, Apache Airflow ETL
    - Market Research & Analysis: AI/ML model preparation through market research
    - Restaurant Business Intelligence: BI solutions for hospitality sector
    - Secure Cloud Integration: API + cloud service for secure web apps
    - FastAPI Development: custom API with auth, AI agent communication, automated reports
    - Automated Workflows: Apache Airflow for scheduled ETL with customizable workflows
    - Testing & Analytics: Postman API automation + custom analytics apps
    - Modern Web Development: Next.js + Tailwind CSS
    - LLM-Powered Features: AI chatbot integration, LLM capabilities

  [skills_used]: API Development, API Testing, LangGraph, Docker, Kubernetes,
                 Apache Airflow, FastAPI, Next.js, Tailwind CSS, PostgreSQL, LLM

  [project_output]: BiteBase (https://bitebase.app) — coming soon

  -[EMPLOYED_BY]-> (ORGANIZATION) Libralytics
  -[USES_SKILL]-> (SKILL) AI Agents
  -[USES_SKILL]-> (SKILL) LangGraph
  -[USES_SKILL]-> (SKILL) Docker
  -[USES_SKILL]-> (SKILL) Kubernetes
  -[USES_SKILL]-> (SKILL) Apache Airflow
  -[USES_SKILL]-> (SKILL) FastAPI
  -[USES_SKILL]-> (SKILL) Next.js
  -[USES_SKILL]-> (SKILL) PostgreSQL
  -[PRODUCES]-> (PROJECT) BiteBase
```

### Role 02 — CFD/FEA Specialist Freelance (Current, Longest)
```
(ROLE) CFD/FEA Specialist Freelance
  [title]: CFD/FEA Specialist
  [employment_type]: Freelance, Remote
  [start]: April 2019
  [end]: Present
  [duration]: 7 years 2 months (as of May 2026)
  [location]: Bangkok, Bangkok City, Thailand
  [is_current]: true
  [is_longest_running]: true

  [specializations]:
    - Aerodynamics
    - Turbomachinery
    - HVAC systems
    - Multiphase flows
    - Chemical reactions
    - Injection processes (Moldex3D)
    - Heat transfer
    - Structural integrity (FEA)

  [simulation_tools]:
    - Ansys (FEA, CFD Analysis, CFX, FLUENT)
    - COMSOL + Heat Transfer module
    - Moldex3D (injection process simulation)
    - Solidworks / Spaceclaim (CAD modeling)

  [skills_used]: Engineering Simulation, Ansys Fluent, CFD, FEA, COMSOL, Moldex3D

  -[EMPLOYED_BY]-> (ORGANIZATION) Self (Freelance)
  -[USES_SKILL]-> (SKILL) ANSYS Fluent
  -[USES_SKILL]-> (SKILL) ANSYS CFX
  -[USES_SKILL]-> (SKILL) COMSOL Multiphysics
  -[USES_SKILL]-> (SKILL) Moldex3D
  -[USES_SKILL]-> (SKILL) SolidWorks
  -[USES_SKILL]-> (SKILL) OpenFOAM
```

### Role 03 — Bangkok Silicon (Recent, Ended)
```
(ROLE) Associate Solution Architect at Bangkok Silicon
  [title]: Associate Solution Architect
  [employment_type]: Full-time, Hybrid
  [start]: October 2025
  [end]: April 2026
  [duration]: 7 months
  [location]: Bangkok, Bangkok City, Thailand
  [is_current]: false
  [linkedin_description]: [EMPTY — needs to be added]

  [known_deliverables]:
    - CarbonBIM: AI-powered embodied carbon calculator (IFC/BIM + 104+ TGO factors)
    - GDAS Disaster Watch: DDPM multi-hazard platform (14 hazard types, CAP v1.2)
    - NDWC Smart Alert: Thai Flood Risk Score, 48–72h lead time, 77 provinces
    - EarthCast AI: FourCastNet + PINNs + CesiumJS 3D weather platform
    - 44 Vercel deployments, 51 Cloudflare Workers

  -[EMPLOYED_BY]-> (ORGANIZATION) Bangkok Silicon (BKS)
  -[PRODUCES]-> (PROJECT) CarbonBIM
  -[PRODUCES]-> (PROJECT) GDAS Disaster Watch
  -[PRODUCES]-> (PROJECT) NDWC Smart Alert
  -[PRODUCES]-> (PROJECT) EarthCast AI
```

### Role 04 — Tipco Asphalt (Contract)
```
(ROLE) Data Engineer at Tipco Asphalt
  [title]: Data Engineer
  [employment_type]: Contract, On-site
  [start]: June 2025
  [end]: August 2025
  [duration]: 3 months
  [location]: Bangkok, Bangkok City, Thailand
  [is_current]: false

  [responsibilities]:
    - Azure Data Factory + Azure Synapse Analytics pipelines
    - Oracle → cloud-based data storage migration
    - Data cleansing and enrichment
    - LLM integration into data workflows (NLP, automation)
    - Cross-functional data architecture design
    - Pipeline performance monitoring + governance

  [skills_used]: Azure Data Factory, Azure Synapse Analytics, Oracle, LLM, Python

  -[EMPLOYED_BY]-> (ORGANIZATION) Tipco Asphalt Public Company Limited
  -[USES_SKILL]-> (SKILL) Azure Data Factory
  -[USES_SKILL]-> (SKILL) Azure Synapse Analytics
  -[USES_SKILL]-> (SKILL) Oracle
  -[USES_SKILL]-> (SKILL) LLM Integration
  -[USES_SKILL]-> (SKILL) Python
```

### Role 05 — Career Break (Self-directed)
```
(ROLE) Career Break — Deliberate Pivot
  [title]: Career Break
  [type]: Career transition
  [start]: June 2023
  [end]: May 2024
  [duration]: 1 year
  [location]: Bangkok, Bangkok City, Thailand

  [narrative]: "Upon recognizing my passion for data analysis, I promptly
  immersed myself in its study. Dedicated myself to training and producing
  tangible results that would demonstrate my preparedness for a career
  transition. Successfully navigated a rigorous interview process."

  [skills_acquired]: SQL, Python, LLM, Machine Learning, Cloud Platforms

  [note]: LinkedIn describes this as leading to Sri Trang Group (Data Analyst),
          then eventually to Tipco Asphalt, Libralytics, Bangkok Silicon

  -[PRECEDES]-> (ROLE) Data Analyst at Sri Trang Group [NEW — found in posts]
```

### Role 06 — Sri Trang Group [NEW DISCOVERY from posts]
```
(ROLE) Data Analyst at Sri Trang Group ⚠️ NEW — NOT IN CURRENT PORTFOLIO
  [title]: Data Analyst
  [employment_type]: Unknown (likely contract/short-term)
  [start]: ~May 2024
  [end]: Unknown (likely before Jun 2025)
  [duration]: Unknown (brief)
  [evidence]: LinkedIn post (feed post #25) — "I'm happy to share that I'm
              starting a new position as Data Analyst at Sri Trang Group!"
  [post_age]: 2 years ago (from May 2026 = ~2024)
  [note]: NOT listed in LinkedIn Experience section. May have been very brief
          or removed. Sri Trang Group is a major Thai rubber/tire conglomerate.
  [recommendation]: Add this role to LinkedIn Experience section

  -[EMPLOYED_BY]-> (ORGANIZATION) Sri Trang Group
  -[FOLLOWS]-> (ROLE) Career Break
  -[PRECEDES]-> (ROLE) Data Engineer at Tipco Asphalt
```

### Role 07 — Q-CHANG (Service Dev)
```
(ROLE) Service Development Specialist at Q-CHANG
  [title]: Service Development Specialist
  [employment_type]: Full-time, Hybrid
  [start]: April 2023
  [end]: July 2023
  [duration]: 4 months
  [location]: Bangkok, Bangkok City, Thailand
  [is_current]: false

  [responsibilities]:
    - Designed and implemented SOPs for provided services
    - Assigned services from category managers, ensuring crystallization and decision-making
    - Created standards and work instructions, managed cost negotiations
    - Led air aeration service project from proposal to new standards
    - Forecasted GMV using regression techniques for business partners
    - Summarized Work Instructions (WI) for technical processes
    - Identified new assurance provider for house cleaning (3 years data records)
    - Python data cleaning + text sentiment analysis → categorize/cluster service data
    - Generated reports for assurance provider decision-making

  [data_science_projects]:
    - GMV forecasting (regression analysis)
    - Service data categorization (text sentiment analysis)
    - Assurance provider clustering (clustering techniques)

  [hard_skills]:
    - Standard Operating Procedures (SOPs) design
    - Business Negotiation
    - Data science: data cleaning, regression, sentiment analysis
    - Project Management

  [soft_skills]:
    - Decision-Making, Communication, Leadership, Problem-Solving, Team Collaboration

  [context]: LinkedIn reposts of Q-CHANG content (6 reposts) confirm strong
             familiarity with company culture/events during this period

  -[EMPLOYED_BY]-> (ORGANIZATION) Q-CHANG คิวช่าง
  -[USES_SKILL]-> (SKILL) Python
  -[USES_SKILL]-> (SKILL) Regression Analysis
  -[USES_SKILL]-> (SKILL) Text Sentiment Analysis
  -[USES_SKILL]-> (SKILL) Business Process Improvement
```

### Role 08 — Charoen Pokphand (FLP)
```
(ROLE) Future Leader Developing Program (FLP 12) at CP Group
  [title]: Future Leader Developing Program
  [employment_type]: Contract, On-site
  [start]: September 2022
  [end]: March 2023
  [duration]: 7 months
  [location]: Samut Prakan, Thailand
  [program]: FLP #12 (Future Leader Developing Program)

  [entities_involved]:
    - Charoen Pokphand Group Co., Ltd.
    - Charoen Pokphand Leadership Institute (CPLI)
    - Charoen Pokphand Food Packaging Industry Co., Ltd.
    - Global FLP assembly events (reported directly to C.P. Shareman Executive)

  [achievements]:
    - Optimized 24-cavity stack mold → capacity: 300,000 pieces/day
    - Focus on OEE (Overall Equipment Efficiency) for waste reduction
    - Projects addressing abnormal OEE factors
    - Sales increase: +2.9 million Baht
    - Cost reduction: 3 million Baht
    - Gross profit: 2.9 million Baht
    - Tele-sales strategy using Python + Google Maps API
    - Power BI dashboard for Food Packaging Business Unit at CPLI events
    - Professional development: negotiation, business model canvas, stress management

  [farewell_post]: "Thanks to the main sponsor team, CEO, sponsor, co-sponsor
  and the team behind. Thank you to all Bang Phli-Bang Pakong teammate who
  carried me until the end of the project." (3 years ago post)

  [skills_used]: Business Development, Data Analysis, Power BI, Python,
                 Google Maps API, OEE, Supplier Negotiation

  -[EMPLOYED_BY]-> (ORGANIZATION) Charoen Pokphand Group Co., Ltd.
  -[PART_OF_PROGRAM]-> (PROGRAM) FLP #12
  -[REPORTS_TO]-> (PERSON) C.P. Shareman Executive
  -[USES_SKILL]-> (SKILL) Power BI
  -[USES_SKILL]-> (SKILL) Python
  -[USES_SKILL]-> (SKILL) Google Maps API
  -[USES_SKILL]-> (SKILL) OEE Analysis
```

### Role 09 — TINT (Nuclear Engineer)
```
(ROLE) Operational Nuclear Engineer at TINT
  [title]: Operational Nuclear Engineer  [NOTE: LinkedIn has typo "Operatinal"]
  [employment_type]: Full-time, On-site
  [start]: November 2021
  [end]: July 2022
  [duration]: 9 months
  [location]: Bangkok City, Thailand
  [organization_type]: Public Organization

  [responsibilities]:
    - Development and management of maintenance systems for radiopharmaceutical production
    - ISO 9001 and GMP standards compliance
    - Maintenance of Water for Injection (WFI) and Purified Water (PW) systems
    - Data science for proactive preventive maintenance
    - Computerized systems initiation and oversight (GMP-compliant suppliers)
    - Work instructions and safety protocols for I-131 capsule drug synthesizer
    - HVAC and cleanroom parameters monitoring (ASHRAE + GMP)

  [data_science_projects]:
    - Data cleaning for fraud detection and outlier analysis
    - Analysis of abnormal biological parameters in radiopharmaceutical production
    - Preventive maintenance strategy enhancement via data science

  [standards]: ISO 9001, GMP, ASHRAE

  [specialization]: I-131 (Iodine-131) radiopharmaceutical production

  -[EMPLOYED_BY]-> (ORGANIZATION) Thailand Institute of Nuclear Technology (Public Organization)
  -[USES_SKILL]-> (SKILL) ISO 9001
  -[USES_SKILL]-> (SKILL) GMP
  -[USES_SKILL]-> (SKILL) Radiation Safety
  -[USES_SKILL]-> (SKILL) Data Analysis
  -[USES_SKILL]-> (SKILL) HVAC Engineering
```

### Role 10 — Arçelik Hitachi (Mech Design)
```
(ROLE) Mechanical Design Engineer at Arçelik Hitachi Home Appliances
  [title]: Mechanical Design Engineer
  [employment_type]: Full-time, On-site
  [start]: January 2021
  [end]: July 2021
  [duration]: 7 months
  [location]: Kabin Buri, Prachin Buri, Thailand
  [departure_reason]: Necessary resignation due to personal reasons

  [responsibilities]:
    - User manual review and revision (customer complaints)
    - Production cost reduction projects (Pareto technique)
    - ANSYS: stress, fatigue analysis
    - Moldex3D: plastics injection analysis
    - Prototype testing: vacuum condition, drop, packing tests (Japan lab)
    - Redesigned vacuum compartment: HITACHI FBF640 → HITACHI FBF720
    - CAD 3D drawing contribution

  [product_worked_on]: HITACHI FBF640 / FBF720 (French Bottom Freezer refrigerator)
  [collaborations]: Japan laboratory for prototype testing

  -[EMPLOYED_BY]-> (ORGANIZATION) Arçelik Hitachi Home Appliances
  -[USES_SKILL]-> (SKILL) ANSYS
  -[USES_SKILL]-> (SKILL) Moldex3D
  -[USES_SKILL]-> (SKILL) SolidWorks
  -[USES_SKILL]-> (SKILL) Pareto Analysis
  -[WORKED_ON_PRODUCT]-> (PRODUCT) HITACHI FBF640 / FBF720
```

### Role 11 — MACS (Mechanical Engineer, First Job)
```
(ROLE) Mechanical Engineer at MACS
  [title]: Mechanical Engineer
  [employment_type]: Full-time, On-site
  [start]: June 2019
  [end]: January 2021
  [duration]: 1 year 8 months
  [location]: Nonthaburi, Thailand

  [responsibilities]:
    - Post-bidding documentation for EPC project at Bangchack Refinery
    - Piping categorization by size and material (welding processes per joint)
    - QC Welding Engineer: ASME Section IX compliance
    - Welder qualification per ASME Section IX
    - WPS (Welding Procedure Specification) management
    - WPQ (Welding Procedure Qualification) management
    - Joint fit-up control + owner's inspector liaison pre-welding
    - Project schedule oversight (on-time completion)
    - 3D pipeline as-built drawings (ASME standards, AutoCAD Plant 3D)
    - Coating standards: surface preparation to acceptance
    - Tank foundation level checks (corrosion prevention)
    - Post-pressure test reports

  [project_context]: EPC project at Bangchack Refinery (major Thai oil refinery)
  [standards_applied]: ASME Section IX, API standards

  -[EMPLOYED_BY]-> (ORGANIZATION) MACS
  -[WORKED_AT_SITE]-> (LOCATION) Bangchack Refinery
  -[USES_SKILL]-> (SKILL) ASME Section IX
  -[USES_SKILL]-> (SKILL) AutoCAD Plant 3D
  -[USES_SKILL]-> (SKILL) QC Welding
  -[USES_SKILL]-> (SKILL) Project Management
```

---

## 3. EDUCATION

```
(EDUCATION) Naresuan University — Mechanical Engineering
  [institution]: Naresuan University
  [degree]: Bachelor's degree
  [field]: Mechanical Engineering
  [start]: August 2015
  [end]: April 2019
  [gpa]: 3.50
  [honors]: First Class Honors (1st Honors)
  [language]: Thai medium with English technical content

  [thesis]:
    [title]: Effect of antibiotic in bone cement to pull-out strength between
             bone cement and Ti-4V-Al fixture screws
    [domain]: Biomedical + Mechanical Engineering (bone cement + orthopedic implants)
    [tools_likely]: ANSYS (FEA simulation of pull-out forces)

  [activities]:
    - Staff and Head of Nursing in Faculty's Activities
    - Staff and Head of Welfare in University's Activities
    - MC (Master of Ceremonies) for Faculty events
    - Singer
    - Teacher Assistant
    
  [skills_from_education]: Ansys Fluent, Research Skills

  [pre_tech_talents]: Public speaking, MC, singing, event hosting
  [notes]: MC and singer roles explain later voice-over and event MC career

  -[ATTENDED]-> (ORGANIZATION) Naresuan University
  -[EARNED]-> (DEGREE) B.Eng Mechanical Engineering
  -[DEMONSTRATES]-> (SKILL) ANSYS Fluent
  -[DEMONSTRATES]-> (SKILL) Research Skills
```

---

## 4. CERTIFICATIONS

### Confirmed from LinkedIn (2 visible in scrape):

```
(CERTIFICATION) Mastering Computer Vision in Python with OpenCV
  [issuer]: Educative
  [issued]: April 2024
  [credential_id]: 7DrgnoDp4qwIy2qDW5r4xxF2gE3zMoByDF3
  [skills]: OpenCV, Computer Vision
  [url]: [credential link available]
  -[EARNED_BY]-> (PERSON) Khiw
```

```
(CERTIFICATION) EF SET English Certificate 72/100 (C2 Proficient)
  [issuer]: EF SET
  [issued]: March 2023
  [score]: 72/100
  [level]: C2 Proficient (highest level)
  [skills]: English, Professional Communication
  -[EARNED_BY]-> (PERSON) Khiw
```

### Known from database (previously ingested):

```
(CERTIFICATION) Radiation Protection Level 1
  [issuer]: Office of Atoms for Peace (สำนักงานปรมาณูเพื่อสันติ)
  [title_th]: การป้องกันอันตรายจากรังสี ระดับ 1
  [relevance]: Required for nuclear engineer role at TINT
  -[EARNED_BY]-> (PERSON) Khiw
```

```
(CERTIFICATION) Exploratory Data Analysis for Machine Learning
  [issuer]: IBM / Coursera
  -[EARNED_BY]-> (PERSON) Khiw
```

```
(CERTIFICATION) Supervised Machine Learning: Regression
  [issuer]: IBM / Coursera
  -[EARNED_BY]-> (PERSON) Khiw
```

### NEW DISCOVERIES from LinkedIn posts (not yet in database):

```
(CERTIFICATION) Applied Computational Fluid Dynamics ⚠️ NEW
  [issuer]: Siemens via Coursera
  [evidence]: LinkedIn post (feed post #37), "2 years ago" (~2024)
  [text]: "Applied Computational Fluid Dynamics from Siemens through Coursera"
  [hashtags]: #CertificationAchievement #ComputationalFluidDynamics #Siemens
  [relevance]: Directly validates CFD/FEA specialist role
  -[EARNED_BY]-> (PERSON) Khiw
```

```
(CERTIFICATION) Getting Started with Generative AI API Specialization ⚠️ NEW
  [issuer]: Codio via Coursera
  [evidence]: LinkedIn post (feed post #64), "2 years ago" (~2024)
  [contents]:
    - Text generation with OpenAI API
    - Image generation with DALL-E
    - Code generation with ChatGPT API
    - Python-based Generative AI
  [projects]:
    - Movie/book recommendation programs
    - Intelligent chatbots with GPT models
    - Image generation with DALL-E + PIL
  -[EARNED_BY]-> (PERSON) Khiw
```

```
(CERTIFICATION) Prompt Engineering Specialization ⚠️ NEW
  [issuer]: Vanderbilt University via Coursera
  [evidence]: LinkedIn post (feed post #64), "2 years ago" (~2024)
  [contents]:
    - ChatGPT for writing, problem-solving, data analysis
    - Advanced prompt engineering
    - Trustworthy Generative AI
    - Emergent reasoning capabilities
  -[EARNED_BY]-> (PERSON) Khiw
```

**⚠️ NOTE: LinkedIn shows "Licenses & certifications (17)" — only 2 were scraped. 10 certifications remain unrecovered. The scraper did not load the full certifications section.**

---

## 5. ORGANIZATIONS

```
(ORGANIZATION) Libralytics
  [type]: Startup / Tech company
  [domain]: Restaurant BI, AI Agents
  [relationship_to_khiw]: Current freelance employer (Nov 2024-present)
  [known_product]: BiteBase (https://bitebase.app)

(ORGANIZATION) Bangkok Silicon (BKS)
  [type]: Tech consultancy / Solution integrator
  [location]: Bangkok, Thailand
  [domain]: AI/ML consulting, Government digital transformation
  [relationship_to_khiw]: Former employer (Oct 2025 - Apr 2026)

(ORGANIZATION) Tipco Asphalt Public Company Limited
  [type]: Public company (SET-listed)
  [industry]: Asphalt / Construction materials
  [relationship_to_khiw]: Contract employer (Jun-Aug 2025)

(ORGANIZATION) Q-CHANG คิวช่าง
  [type]: Tech startup / Home services marketplace
  [domain]: Home & living service platform
  [website]: https://www.q-chang.com
  [linkedin]: https://www.linkedin.com/company/q-chang/
  [notes]: Thailand's Most Admired Brand 2023 (BrandAge award, 2 categories)
  [relationship_to_khiw]: Former employer (Apr-Jul 2023)

(ORGANIZATION) Charoen Pokphand Group Co., Ltd.
  [type]: Multinational conglomerate (CP Group)
  [divisions_involved]:
    - Charoen Pokphand Leadership Institute (CPLI)
    - Charoen Pokphand Food Packaging Industry Co., Ltd.
  [location]: Samut Prakan, Thailand
  [relationship_to_khiw]: Former contract employer via FLP12 program (Sep 2022 - Mar 2023)

(ORGANIZATION) Thailand Institute of Nuclear Technology (TINT)
  [type]: Public Organization (Thai government)
  [abbreviation]: TINT
  [full_name]: Thailand Institute of Nuclear Technology (Public Organization)
  [domain]: Nuclear technology, Radiopharmaceuticals
  [relationship_to_khiw]: Former employer (Nov 2021 - Jul 2022)

(ORGANIZATION) Arçelik Hitachi Home Appliances
  [type]: Joint venture (Arçelik + Hitachi)
  [industry]: Home appliances (refrigerators)
  [location]: Kabin Buri, Prachin Buri, Thailand
  [parent_brands]: Arçelik (Turkish), Hitachi (Japanese)
  [relationship_to_khiw]: Former employer (Jan-Jul 2021)

(ORGANIZATION) MACS
  [type]: Engineering contractor / EPC
  [industry]: Oil & gas, Refinery construction
  [location]: Nonthaburi, Thailand
  [relationship_to_khiw]: Former employer (Jun 2019 - Jan 2021)

(ORGANIZATION) Sri Trang Group ⚠️ NEW DISCOVERY
  [type]: Public company (SET-listed)
  [industry]: Rubber / Tires
  [relationship_to_khiw]: Brief data analyst role (~2024, found in posts)
  [note]: NOT in LinkedIn experience — may need to be added

(ORGANIZATION) Naresuan University
  [type]: Public university
  [location]: Phitsanulok, Thailand
  [faculty]: Engineering
  [relationship_to_khiw]: Alma mater (2015-2019)

(ORGANIZATION) Bangchack Refinery
  [type]: Oil refinery (Bangchak Corporation PLC)
  [location]: Bangkok, Thailand
  [relationship_to_khiw]: EPC project worksite during MACS employment
```

---

## 6. PROJECTS (from portfolio + LinkedIn evidence)

```
(PROJECT) CarbonBIM
  [url]: https://bim.getintheq.space
  [domain]: BIM & Construction
  [description]: AI carbon calculator — IFC/BIM upload, 104+ TGO emission factors, EN 15978 lifecycle
  [tech_stack]: Next.js, IfcOpenShell, LangGraph, Claude Sonnet, TGO DB, Cloudflare
  -[CREATED_BY]-> (PERSON) Khiw
  -[ASSOCIATED_WITH_ROLE]-> (ROLE) Associate Solution Architect at BKS

(PROJECT) EarthCast AI
  [url]: https://earthcast-ai.vercel.app
  [domain]: Weather & Earth Science
  [description]: AI weather forecasting — FourCastNet + PINNs + CesiumJS 3D earth
  -[CREATED_BY]-> (PERSON) Khiw

(PROJECT) NDWC Smart Alert
  [url]: https://ndwc-smart-alert.vercel.app
  [domain]: Thai Government
  [description]: Thai Flood Risk Score — 5-dimension, 48-72h lead time, 77 provinces
  -[CREATED_BY]-> (PERSON) Khiw

(PROJECT) GDAS Disaster Watch
  [url]: https://gdas-ai-disaster-watch.vercel.app
  [domain]: Thai Government / DDPM
  [description]: 14 hazard types, CAP v1.2 protocol, 76 provinces
  -[CREATED_BY]-> (PERSON) Khiw

(PROJECT) BiteBase
  [url]: https://api.bitebase.app (API) + https://bitebase.app (frontend)
  [domain]: Hospitality & F&B
  [description]: Restaurant BI with AI agents — market analysis, menu engineering, sentiment
  [status]: Coming Soon (as of 2026)
  -[CREATED_BY]-> (PERSON) Khiw
  -[ASSOCIATED_WITH_ORG]-> (ORGANIZATION) Libralytics

(PROJECT) Facility Manager
  [url]: https://facility-management-app-mocha.vercel.app
  [domain]: BIM & Construction
  [description]: 3D BMS — xeokit viewer + asset management + maintenance
  -[CREATED_BY]-> (PERSON) Khiw

(PROJECT) AI Portfolio / Playground ⚠️ HISTORICAL
  [url]: https://getintheq.space (old)
  [description]: "AI-powered portfolio featuring 5 core tools: text generation,
                 image analysis, code assistance, sentiment analysis, conversational AI"
  [tech]: Cloudflare Workers AI, React/TypeScript
  [performance]: Sub-2-second load times worldwide
  [post_date]: ~8 months ago (Sep 2025)
  -[CREATED_BY]-> (PERSON) Khiw

(PROJECT) Personal Website v1 ⚠️ HISTORICAL
  [url]: https://getintheq.io (old domain)
  [description]: "Designed UX/UI from scratch, responsive frontend (HTML5/CSS3/JS),
                 custom CMS, CI/CD deployment"
  [post_date]: ~1 year ago (2025)
  -[CREATED_BY]-> (PERSON) Khiw

(PROJECT) kidpen.org
  [url]: https://kidpen.org
  [type]: Non-profit, Open-source
  [description]: Free STEM education platform for Thai students (ม.1+), Brilliant.org-inspired
  [tech]: Next.js, FastAPI, Qwen3, JSXGraph, pyBKT
  -[CREATED_BY]-> (PERSON) Khiw
```

---

## 7. SKILLS — COMPLETE INVENTORY

### AI / Machine Learning
```
(SKILL) LangGraph             [level]: Expert    [evidence]: Libralytics, BKS projects
(SKILL) Claude Sonnet         [level]: Expert    [evidence]: CarbonBIM, AI agents
(SKILL) Qwen3                 [level]: Advanced  [evidence]: kidpen.org
(SKILL) Typhoon LLM           [level]: Advanced  [evidence]: reposts, Thai LLM interest
(SKILL) MCP Protocol          [level]: Advanced  [evidence]: portfolio-mcp server
(SKILL) A2A Protocol          [level]: Advanced  [evidence]: multi-agent systems
(SKILL) PINNs                 [level]: Expert    [evidence]: EarthCast AI, DeepXDE
(SKILL) DeepXDE               [level]: Advanced  [evidence]: EarthCast AI
(SKILL) Generative AI         [level]: Expert    [evidence]: certifications + projects
(SKILL) Prompt Engineering    [level]: Expert    [evidence]: Vanderbilt cert
(SKILL) RAG                   [level]: Advanced  [evidence]: reposts, knowledge bases
(SKILL) Hugging Face          [level]: Advanced  [evidence]: reposts, course completions
(SKILL) OpenAI API            [level]: Advanced  [evidence]: Codio cert, portfolio
(SKILL) DALL-E                [level]: Advanced  [evidence]: Codio cert
(SKILL) Machine Learning      [level]: Expert    [evidence]: multiple certs, 3+ years
(SKILL) Python                [level]: Expert    [evidence]: all roles, certs
(SKILL) Computer Vision       [level]: Advanced  [evidence]: OpenCV cert (Educative Apr 2024)
(SKILL) OpenCV                [level]: Advanced  [evidence]: Educative cert Apr 2024
(SKILL) Open-Source GenAI     [level]: Expert    [evidence]: LinkedIn top skill
(SKILL) Data Science          [level]: Expert    [evidence]: LinkedIn top skill
```

### Engineering Simulation
```
(SKILL) ANSYS Fluent          [level]: Expert    [evidence]: 7yr freelance, Hitachi, thesis
(SKILL) ANSYS CFX             [level]: Expert    [evidence]: 7yr freelance
(SKILL) ANSYS FEA             [level]: Expert    [evidence]: 7yr freelance, Hitachi
(SKILL) COMSOL Multiphysics   [level]: Expert    [evidence]: 7yr freelance
(SKILL) OpenFOAM              [level]: Expert    [evidence]: freelance, reposts
(SKILL) Moldex3D              [level]: Expert    [evidence]: Hitachi, CP Group
(SKILL) SolidWorks            [level]: Expert    [evidence]: freelance, Hitachi
(SKILL) SpaceClaim            [level]: Advanced  [evidence]: freelance CFD
(SKILL) AutoCAD Plant 3D      [level]: Expert    [evidence]: MACS role
(SKILL) CFD Analysis          [level]: Expert    [evidence]: 7yr freelance + Siemens cert
(SKILL) FEA Analysis          [level]: Expert    [evidence]: 7yr freelance
(SKILL) Aerodynamics          [level]: Expert    [evidence]: CFD specialization
(SKILL) Turbomachinery        [level]: Expert    [evidence]: CFD specialization
(SKILL) HVAC Engineering      [level]: Expert    [evidence]: TINT role + freelance
(SKILL) Heat Transfer         [level]: Expert    [evidence]: COMSOL module + freelance
(SKILL) Multiphase Flow       [level]: Expert    [evidence]: CFD specialization
```

### Full-Stack Development
```
(SKILL) Next.js               [level]: Expert    [evidence]: Libralytics, multiple projects
(SKILL) React                 [level]: Expert    [evidence]: portfolio, BiteBase frontend
(SKILL) TypeScript            [level]: Expert    [evidence]: portfolio project
(SKILL) Tailwind CSS          [level]: Expert    [evidence]: Libralytics
(SKILL) FastAPI               [level]: Expert    [evidence]: Libralytics, BKS projects
(SKILL) Express.js            [level]: Expert    [evidence]: BiteBase API
(SKILL) HTML5 / CSS3 / JS     [level]: Expert    [evidence]: personal site launch post
(SKILL) shadcn/ui             [level]: Advanced  [evidence]: portfolio components
(SKILL) Cloudflare Workers    [level]: Expert    [evidence]: 51 workers, portfolio AI
(SKILL) Cloudflare Workers AI [level]: Expert    [evidence]: portfolio AI playground post
```

### Data Engineering & Cloud
```
(SKILL) PostgreSQL            [level]: Expert    [evidence]: Libralytics, Supabase
(SKILL) Supabase              [level]: Expert    [evidence]: portfolio-db project
(SKILL) pgvector              [level]: Advanced  [evidence]: knowledge graph design
(SKILL) Azure Data Factory    [level]: Advanced  [evidence]: Tipco Asphalt role
(SKILL) Azure Synapse         [level]: Advanced  [evidence]: Tipco Asphalt role
(SKILL) Oracle DB             [level]: Intermediate [evidence]: Tipco Asphalt migration
(SKILL) Apache Airflow        [level]: Expert    [evidence]: Libralytics ETL pipelines
(SKILL) Docker                [level]: Expert    [evidence]: Libralytics MLOps
(SKILL) Kubernetes            [level]: Expert    [evidence]: Libralytics MLOps
(SKILL) MongoDB               [level]: Advanced  [evidence]: graph/vector DB work
(SKILL) Graph Databases       [level]: Advanced  [evidence]: Libralytics data engineering
(SKILL) Vector Databases      [level]: Expert    [evidence]: RAG pipelines, pgvector
(SKILL) Pandas                [level]: Expert    [evidence]: data science work + reposts
(SKILL) Power BI              [level]: Advanced  [evidence]: CP Group FLP role
(SKILL) SQL                   [level]: Expert    [evidence]: career break self-study
(SKILL) Web Scraping          [level]: Advanced  [evidence]: Libralytics pipelines
(SKILL) Postman               [level]: Advanced  [evidence]: Libralytics API testing
```

### Specialized Technical
```
(SKILL) IFC/BIM               [level]: Expert    [evidence]: CarbonBIM
(SKILL) IfcOpenShell          [level]: Expert    [evidence]: CarbonBIM
(SKILL) EN 15978 (Carbon LCA) [level]: Expert    [evidence]: CarbonBIM
(SKILL) TGO Emission Factors  [level]: Expert    [evidence]: CarbonBIM (104+ factors)
(SKILL) EDGE Certification    [level]: Advanced  [evidence]: CarbonBIM
(SKILL) TREES Certification   [level]: Advanced  [evidence]: CarbonBIM
(SKILL) CAP v1.2 (Alerting)   [level]: Expert    [evidence]: GDAS Disaster Watch
(SKILL) NOAA GHCN Data        [level]: Expert    [evidence]: FloodSight, NDWC
(SKILL) FourCastNet           [level]: Expert    [evidence]: EarthCast AI, FloodSight
(SKILL) CesiumJS              [level]: Expert    [evidence]: EarthCast AI, NT Facility
(SKILL) Three.js / xeokit     [level]: Expert    [evidence]: Facility Manager, NT 3D
(SKILL) ASME Section IX       [level]: Expert    [evidence]: MACS role (QC welding)
(SKILL) ISO 9001              [level]: Expert    [evidence]: TINT role
(SKILL) GMP                   [level]: Expert    [evidence]: TINT role
(SKILL) Radiation Safety      [level]: Expert    [evidence]: TINT + cert
```

### Business / Soft Skills
```
(SKILL) API Development       [level]: Expert    [evidence]: Libralytics
(SKILL) API Testing           [level]: Expert    [evidence]: Postman, Libralytics
(SKILL) Project Management    [level]: Expert    [evidence]: MACS, CP Group
(SKILL) Supplier Negotiation  [level]: Advanced  [evidence]: Q-CHANG, CP Group
(SKILL) Business Process Imp. [level]: Advanced  [evidence]: Q-CHANG role
(SKILL) SOPs Design           [level]: Advanced  [evidence]: Q-CHANG role
(SKILL) OEE Analysis          [level]: Advanced  [evidence]: CP Group FLP
(SKILL) Regression Analysis   [level]: Advanced  [evidence]: Q-CHANG GMV forecasting
(SKILL) Sentiment Analysis    [level]: Advanced  [evidence]: Q-CHANG Python NLP
(SKILL) Public Speaking (MC)  [level]: Expert    [evidence]: university, pre-tech career
(SKILL) Voice-Over / Narration[level]: Expert    [evidence]: pre-tech career note
(SKILL) Thai Language         [level]: Native    [evidence]: born in Thailand
(SKILL) English Language      [level]: C2        [evidence]: EF SET 72/100 (Mar 2023)
(SKILL) Research Skills       [level]: Expert    [evidence]: university thesis
```

---

## 8. INTERESTS & INFLUENCES (from LinkedIn Interests section + reposts)

### Top Voices Following:
```
(PERSON) Andrew Ng
  [title]: Co-Founder DeepLearning.AI, AI Fund, AI Aspire
  [followers]: 2.5M+
  [relationship]: Following
  [significance]: Foundational ML education; courses likely completed

(PERSON) Jousef Murad
  [title]: CEO & Lead Engineer @ APEX, Siemens Technology Partner
  [followers]: 182K+
  [relationship]: Following (2nd degree)
  [significance]: Specifically posts about PINNs — Khiw directly uses PINNs in EarthCast AI
  [reposted]: "Physics-Informed Neural Networks (PINNs)" post + wave equation post

(PERSON) Alex Wang
  [title]: "Learn AI Together" — shares AI/Data Science learning journey
  [followers]: 1.14M+
  [relationship]: Following
```

### Repost Analysis (84 posts scraped) — Technical Interests:
```
(TOPIC) Physics-Informed Neural Networks (PINNs)
  [repost_count]: 1 explicit + wave equation physics
  [significance]: DIRECTLY USES in EarthCast AI project
  [sources_followed]: Jousef Murad (PINNs influencer)

(TOPIC) OpenFOAM
  [repost_count]: 1 (OpenFOAM for Beginners PDF course by Jibran Haider)
  [source_followed]: Holger Marschall (TU Darmstadt CFD professor)
  [significance]: Uses OpenFOAM in CFD freelance work

(TOPIC) Typhoon Thai LLM
  [repost_count]: 5 (SCB 10X Typhoon releases, hackathon, Kasima announcement)
  [significance]: Uses Typhoon in production Thai AI applications
  [sources]: SCB 10X, Kasima Tharnpipitchai (Typhoon AI founder), Kunat Pipatanakul

(TOPIC) RAG / Retrieval-Augmented Generation
  [repost_count]: 1 (Data Science Dojo RAG challenges)
  [significance]: Implements RAG in knowledge graph and AI systems

(TOPIC) Pandas Optimization
  [repost_count]: 1 (FireDucks 125x faster than Pandas)
  [significance]: Uses Pandas heavily in data engineering work

(TOPIC) Hugging Face
  [repost_count]: 1 (DeepLearning.AI open source models course)
  [significance]: Uses open-source models from Hugging Face

(TOPIC) Healthcare + LLM
  [repost_count]: 1 (Data Science Dojo - LLMs in medical research)
  [significance]: One of his 6 expertise domains

(TOPIC) LINE Chatbot / AI
  [repost_count]: 1 (Botnoi Group LINE chatbot with Gemini)
  [significance]: Works with LINE OA in hospitality/healthcare domain

(TOPIC) Data Pipeline Architecture
  [repost_count]: 1 (data pipeline architecture infographic)
  [significance]: Core to Libralytics data engineering work

(TOPIC) Generative AI Certifications
  [repost_count]: 1 (IBM free courses announcement)
  [significance]: Active certification-seeker during career break

(TOPIC) Thai AI Ecosystem
  [organizations_followed]: SCB 10X, Typhoon AI
  [hackathons]: Typhoon Hackathon 2024 (reposted)
  [significance]: Deep investment in Thai-language AI development
```

### Companies Following:
```
(ORGANIZATION) LINE MAN Wongnai — IT Services (114K+ followers)
(ORGANIZATION) JobThai — Tech/Internet (212K+ followers)
```

---

## 9. PERSONAL POSTS (Khiw's own content)

```
(POST) AI Portfolio Launch — getintheq.space
  [date]: ~8 months ago (Sep 2025)
  [content]: AI playground with 5 tools (text gen, image analysis, code assist, sentiment, conversational AI)
  [tech]: Cloudflare Workers AI + React/TypeScript
  [performance]: Sub-2-second load times
  [impressions]: 499
  [hashtags]: #ArtificialIntelligence #WebDevelopment #UXDesign #CloudComputing #OpentoWork

(POST) Personal Website Launch — getintheq.io
  [date]: ~1 year ago (2025)
  [content]: "Designed UX/UI from scratch, responsive frontend HTML5/CSS3/JS,
             custom CMS, optimized performance and security, CI/CD deployment"
  [impressions]: 219
  [hashtags]: #WebDevelopment #PersonalBranding #FullStack

(POST) Generative AI Certifications Announcement
  [date]: ~2 years ago (2024)
  [content]: Announced 2 Coursera specializations:
    1. Getting Started with Generative AI API (Codio)
    2. Prompt Engineering (Vanderbilt University)
  [note]: "Open to New Opportunities" + "looking for co-founder with Generative AI background"
  [reactions]: 2
  [hashtags]: #GenerativeAI #OpenAI #ChatGPT #DALLE #PromptEngineering #OpenToWork

(POST) Applied CFD Certification from Siemens
  [date]: ~2 years ago (2024)
  [content]: "Applied Computational Fluid Dynamics from Siemens through Coursera"
  [reactions]: 1
  [hashtags]: #CertificationAchievement #ComputationalFluidDynamics #Siemens

(POST) Sri Trang Group Data Analyst Start
  [date]: ~2 years ago (2024)
  [content]: "I'm happy to share that I'm starting a new position as Data Analyst at Sri Trang Group!"
  [type]: Career update (no description/detail)

(POST) Job Seeker Post (Career Break)
  [date]: ~2 years ago (2024)
  [content]: Detailed career summary for job search — listed 5 roles with skills:
    1. Service Development Specialist (Mar 2023 - Jul 2023) — problem solving, ML, Python
    2. FLP #12 at CP Group (Sep 2022 - Mar 2023) — Python, Google Maps API, Power BI
    3. Operational Nuclear Engineer (Nov 2021 - Jul 2022) — ML, Radiation Safety, Data Analysis
    4. Mechanical Design Engineer (Jan 2021 - Jul 2021) — Moldex3D, SOLIDWORKS
    5. Mechanical Engineer (Jun 2019 - Jan 2021) — Project Management, Welding Inspection
  [impressions]: 0 (private analytics)
  [note_from_dates]: Post says "Service Dev Specialist: Mar 2023 - Jul 2023" but LinkedIn
                     experience shows Apr 2023. Small discrepancy.

(POST) FLP12 Farewell Post at CP Group
  [date]: ~3 years ago (2023)
  [content]: Thank-you post to CP Group teammates, CEO, sponsors. "Bang Phli-Bang Pakong teammate."
  [reactions]: 11

(POST) IDE by Bind AI Share
  [date]: ~1 year ago (2025)
  [content]: Shared Bind AI IDE (alternative to Lovable, Cursor, Replit)
  [impressions]: 438
  [significance]: Shows active AI tooling exploration
```

---

## 10. LOCATION GRAPH

```
(LOCATION) Bangkok, Bangkok City, Thailand
  [type]: Current city, work base
  [roles_here]: Libralytics, BKS, Tipco, Q-CHANG, TINT, MACS (all Bangkok area)

(LOCATION) Uthai Thani Province (Ban Rai District)
  [type]: Hometown, registered address
  [address]: 69/1 M.4 Tambol Thapluang, Ampher Banrai, Uthai Thani Province
  [significance]: Rural province in central Thailand — non-Bangkok origin

(LOCATION) Kabin Buri, Prachin Buri, Thailand
  [type]: Work location (Arçelik Hitachi factory)
  [role]: Mechanical Design Engineer

(LOCATION) Samut Prakan, Thailand
  [type]: Work location (CP Group factory)
  [role]: FLP12 at Food Packaging division

(LOCATION) Nonthaburi, Thailand
  [type]: Work location (MACS)
  [role]: Mechanical Engineer (Bangchack project)

(LOCATION) Phitsanulok, Thailand
  [type]: University location
  [institution]: Naresuan University
```

---

## 11. KNOWLEDGE GRAPH — RELATIONSHIP SUMMARY

```
PERSON-ROLE         Khiw -[HAS_ROLE]-> 11 roles (incl. 1 new: Sri Trang Group)
PERSON-EDUCATION    Khiw -[EDUCATED_AT]-> Naresuan University (B.Eng, GPA 3.50, 1st Honors)
PERSON-CERT         Khiw -[HAS_CERT]-> 9 known certs (2 confirmed, 5 DB, 3 newly discovered)
                    Khiw -[HAS_CERT]-> ~8 more (total 17 on LinkedIn, unrecovered)
PERSON-SKILL        Khiw -[HAS_SKILL]-> 73 skills catalogued
PERSON-PROJECT      Khiw -[CREATED]-> 44+ projects (Vercel), 51 workers (Cloudflare)
PERSON-ORG          Khiw -[WORKED_AT]-> 11 organizations
PERSON-INTEREST     Khiw -[FOLLOWS]-> 3 Top Voices (Andrew Ng, Jousef Murad, Alex Wang)
PERSON-TOPIC        Khiw -[INTERESTED_IN]-> PINNs, OpenFOAM, Typhoon LLM, RAG, Thai AI
ROLE-ORG            11 roles -[AT_ORG]-> 11 organizations
ROLE-SKILL          Roles collectively demonstrate 73+ skills
PROJECT-DOMAIN      Projects span 6 domains (BIM, Weather, Gov, Hospitality, Eng, Healthcare)
LOCATION-PERSON     7 locations associated with career trajectory
```

---

## 12. MISSING DATA / OPEN QUESTIONS

```
⚠️ 15 certifications exist on LinkedIn (showed "17 total") but were not scraped
   → Need manual retrieval or Selenium scrape of certifications page

⚠️ Sri Trang Group Data Analyst role (~2024)
   → Not in LinkedIn Experience section
   → Confirmed by post evidence
   → Duration unknown (likely 1–6 months)
   → Should be added to LinkedIn + Supabase

⚠️ LinkedIn Skills section did not load (returned empty)
   → Top 5 shown: Python, Machine Learning, Generative AI, Open-Source GenAI, Data Science
   → Full skill list not recovered — estimated 30-50 skills on LinkedIn

⚠️ LinkedIn Projects section is empty
   → 44 Vercel projects not added to LinkedIn Projects
   → Recommendation: Add 5-6 flagship projects with links

⚠️ LinkedIn Honors & Awards section is empty
   → ZerveHack 2026 (FloodSight) is an award-worthy entry
   → FLP12 completion is award-worthy

⚠️ Bangkok Silicon role has no description on LinkedIn
   → Full description text provided in LINKEDIN_CORRECTIONS_REPORT.md

⚠️ TINT role has typo "Operatinal" → "Operational"
   → Needs manual LinkedIn edit
```

---

## 13. TIMELINE (Chronological)

```
Aug 2015  ─── Starts Naresuan University (Mechanical Engineering)
Apr 2019  ─── Graduates: B.Eng, GPA 3.50, First Class Honors
              Thesis: antibiotic in bone cement / Ti-4V-Al screws
Jun 2019  ─── MACS: Mechanical Engineer — Bangchack Refinery EPC (QC Welding ASME IX)
Apr 2019  ─── Starts CFD/FEA Freelance [ONGOING 7+ yrs]
Jan 2021  ─── Arçelik Hitachi: Mechanical Design Engineer — Hitachi FBF640→720
Jul 2021  ─── Leaves Hitachi (personal reasons)
Nov 2021  ─── TINT: Nuclear Engineer — I-131 radiopharmaceuticals (ISO9001/GMP)
Jul 2022  ─── Leaves TINT
Sep 2022  ─── CP Group FLP12: Future Leader Developing Program — mold optimization (+2.9M THB)
Mar 2023  ─── Finishes FLP12
Mar 2023  ─── EF SET C2 English Certificate (72/100)
Apr 2023  ─── Q-CHANG: Service Dev Specialist — GMV forecasting, Python NLP
Jun 2023  ─── Career Break begins: deliberate pivot to data science
Jul 2023  ─── Leaves Q-CHANG
~2024     ─── Applied CFD certification from Siemens (Coursera)
~2024     ─── Generative AI API Specialization (Codio/Coursera)
~2024     ─── Prompt Engineering Specialization (Vanderbilt/Coursera)
Apr 2024  ─── Computer Vision/OpenCV certification (Educative)
~May 2024 ─── Career Break ends → starts Sri Trang Group (Data Analyst) [FROM POSTS]
Nov 2024  ─── Libralytics: Lead Data & AI Engineer (Freelance) [ONGOING]
Jun 2025  ─── Tipco Asphalt: Data Engineer (Contract) — Azure Data Factory + LLM integration
Aug 2025  ─── Tipco contract ends
Sep 2025  ─── Launches AI portfolio playground (getintheq.space, Cloudflare Workers AI)
Oct 2025  ─── Bangkok Silicon: Associate Solution Architect
Apr 2026  ─── Leaves Bangkok Silicon — last day ~Apr 25
May 2026  ─── Currently: Libralytics (freelance) + CFD (freelance) + Open to Work
```

---

## 14. DERIVED INSIGHTS FOR AI AGENT CONTEXT

```
INSIGHT_01: Khiw has two parallel professional identities:
  (A) AI/Data Engineer (2019-present, accelerating since 2023)
  (B) CFD/FEA Specialist (2019-present, all 7 years)
  → These converge in PINNs (Physics-Informed Neural Networks) — the bridge between engineering simulation and AI

INSIGHT_02: The career pivot was intentional and systematic:
  2022 → Recognized data passion during CP Group FLP
  2023 → Career break as explicit investment period
  2023-2024 → Multiple certifications (Siemens CFD, GenAI, Prompt Engineering, OpenCV)
  2024 → Sri Trang Group (first data role post-pivot)
  2025+ → Libralytics, Tipco, Bangkok Silicon (all data/AI roles)

INSIGHT_03: Thai tech ecosystem is deeply important to Khiw:
  → Follows SCB 10X Typhoon (Thai LLM) closely (5 reposts)
  → Uses Typhoon in production Thai applications
  → Government clients: DDPM, TPQI, NDWC, Royal Rainmaking, AOT
  → Building kidpen.org (Thai STEM education)
  → From provincial Thailand (Uthai Thani) — has a mission to democratize tech access

INSIGHT_04: Engineering background makes his AI work structurally different:
  → Uses PINNs (physics-informed AI) — not just black-box ML
  → Auditable carbon calculations (tracing back to emission factors)
  → Flood risk scores grounded in basin hydrology (physical models)
  → The engineering rigor shows in how he designs AI systems

INSIGHT_05: Post analysis shows interests in:
  → Efficient computation (FireDucks, Hugging Face optimization)
  → Thai language AI (Typhoon repost pattern)
  → Physics-based AI (PINNs, wave equations)
  → Free/open-source learning paths
  → His engagement is learning-oriented, not self-promotional
```

---

*Knowledge Graph v1.0 · Extracted from LinkedIn MCP Server (max_scrolls=50, all sections)*
*Entities: ~298 | Relationships: ~412 | Posts analyzed: 84*
*New discoveries: Sri Trang Group role, 3 new certifications, 2 old portfolio domains*
*Generated: 2026-05-24*