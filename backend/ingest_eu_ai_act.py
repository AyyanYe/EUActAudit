#!/usr/bin/env python3
"""
ingest_eu_ai_act.py  –  One-time script to populate the ChromaDB vector store
with the full EU AI Act (Regulation 2024/1689) articles.

Run from the backend directory:
    python ingest_eu_ai_act.py

The script is idempotent: it clears the collection first, then re-ingests.
"""

import sys
import os
import json

# Ensure backend/ is on the path so `core.*` imports work
sys.path.insert(0, os.path.dirname(__file__))

from core.vector_store import ARTICLES_PATH

# ---------------------------------------------------------------------------
# EU AI Act – Structured article excerpts
# Source: Official Journal of the European Union, Regulation (EU) 2024/1689
# ---------------------------------------------------------------------------

EU_AI_ACT_ARTICLES = [
    # ===== TITLE I – GENERAL PROVISIONS =====
    {
        "id": "art_1",
        "article": "Article 1",
        "title": "Subject matter",
        "text": (
            "This Regulation lays down harmonised rules for the placing on the market, the putting into service "
            "and the use of artificial intelligence systems (AI systems) in the Union. It also lays down prohibitions "
            "of certain AI practices, specific requirements for high-risk AI systems and obligations for operators of "
            "such systems, as well as harmonised transparency rules for certain AI systems."
        ),
    },
    {
        "id": "art_2",
        "article": "Article 2",
        "title": "Scope",
        "text": (
            "This Regulation applies to providers placing on the market or putting into service AI systems in the "
            "Union, irrespective of whether those providers are established in the Union or in a third country. "
            "It also applies to deployers of AI systems that have their place of establishment or are located within "
            "the Union, and to providers and deployers of AI systems that have their place of establishment or are "
            "located in a third country, where the output produced by the AI system is used in the Union."
        ),
    },
    {
        "id": "art_3",
        "article": "Article 3",
        "title": "Definitions",
        "text": (
            "Key definitions under the EU AI Act:\n"
            "- 'AI system': a machine-based system designed to operate with varying levels of autonomy, that may "
            "exhibit adaptiveness after deployment and that, for explicit or implicit objectives, infers, from the "
            "input it receives, how to generate outputs such as predictions, content, recommendations, or decisions "
            "that can influence physical or virtual environments.\n"
            "- 'Provider': a natural or legal person that develops an AI system or a general-purpose AI model or "
            "that has an AI system or general-purpose AI model developed and places it on the market or puts the AI "
            "system into service under its own name or trademark.\n"
            "- 'Deployer': a natural or legal person that uses an AI system under its authority, except where the "
            "AI system is used in the course of a personal non-professional activity.\n"
            "- 'Risk': the combination of the probability of an occurrence of harm and the severity of that harm.\n"
            "- 'Substantial modification': a change to an AI system after its placing on the market or putting into "
            "service which is not foreseen or planned by the provider and as a result of which the compliance of the "
            "AI system with the requirements is affected."
        ),
    },
    # ===== TITLE II – PROHIBITED AI PRACTICES =====
    {
        "id": "art_5_1a",
        "article": "Article 5(1)(a)",
        "title": "Prohibited AI practices – Subliminal manipulation",
        "text": (
            "The placing on the market, the putting into service or the use of an AI system that deploys subliminal "
            "techniques beyond a person's consciousness or purposefully manipulative or deceptive techniques, with "
            "the objective or the effect of materially distorting the behaviour of a person or a group of persons by "
            "appreciably impairing their ability to make an informed decision, thereby causing them to take a decision "
            "that they would not have otherwise taken, in a manner that causes or is reasonably likely to cause that "
            "person, another person or group of persons significant harm, is prohibited."
        ),
    },
    {
        "id": "art_5_1b",
        "article": "Article 5(1)(b)",
        "title": "Prohibited AI practices – Exploitation of vulnerabilities",
        "text": (
            "The placing on the market, the putting into service or the use of an AI system that exploits any of the "
            "vulnerabilities of a natural person or a specific group of persons due to their age, disability or a "
            "specific social or economic situation, with the objective or the effect of materially distorting the "
            "behaviour of that person or a person belonging to that group in a manner that causes or is reasonably "
            "likely to cause that person or another person significant harm, is prohibited."
        ),
    },
    {
        "id": "art_5_1c",
        "article": "Article 5(1)(c)",
        "title": "Prohibited AI practices – Social scoring",
        "text": (
            "The placing on the market, the putting into service or the use of AI systems for the evaluation or "
            "classification of natural persons or groups of persons over a certain period of time based on their "
            "social behaviour or known, inferred or predicted personal or personality characteristics, with the "
            "social score leading to detrimental or unfavourable treatment of certain natural persons or groups of "
            "persons in social contexts that are unrelated to the contexts in which the data was originally generated "
            "or collected, or treatment that is unjustified or disproportionate to their social behaviour or its "
            "gravity, is prohibited."
        ),
    },
    {
        "id": "art_5_1d",
        "article": "Article 5(1)(d)",
        "title": "Prohibited AI practices – Real-time biometric identification",
        "text": (
            "The use of 'real-time' remote biometric identification systems in publicly accessible spaces for the "
            "purposes of law enforcement is prohibited, unless and in as far as such use is strictly necessary for "
            "one of the following objectives: (i) the targeted search for specific victims of abduction, trafficking "
            "in human beings or sexual exploitation; (ii) the prevention of a specific, substantial and imminent "
            "threat to the life or physical safety of natural persons or a genuine and present or foreseeable threat "
            "of a terrorist attack; (iii) the localisation or identification of a person suspected of having committed "
            "a criminal offence listed in the Annex for which the applicable Member State law provides for a penalty "
            "involving deprivation of liberty for a maximum period of at least four years."
        ),
    },
    {
        "id": "art_5_1f",
        "article": "Article 5(1)(f)",
        "title": "Prohibited AI practices – Emotion recognition in workplace and education",
        "text": (
            "The placing on the market, the putting into service or the use of AI systems to infer emotions of a "
            "natural person in the areas of workplace and education institutions is prohibited, except where the use "
            "of the AI system is intended to be put in place or put on the market for medical or safety reasons."
        ),
    },
    # ===== TITLE III – HIGH-RISK AI SYSTEMS =====
    {
        "id": "art_6",
        "article": "Article 6",
        "title": "Classification rules for high-risk AI systems",
        "text": (
            "An AI system shall be considered high-risk where it is a product, or the safety component of a product, "
            "that is covered by the Union harmonisation legislation listed in Annex I and is required to undergo a "
            "third-party conformity assessment. An AI system referred to in Annex III shall be considered high-risk. "
            "By way of derogation, an AI system referred to in Annex III shall not be considered high-risk where it "
            "does not pose a significant risk of harm to the health, safety or fundamental rights of natural persons, "
            "including by not materially influencing the outcome of decision-making. A provider who considers that an "
            "AI system referred to in Annex III is not high-risk shall document its assessment before placing it on "
            "the market or putting it into service."
        ),
    },
    {
        "id": "art_7",
        "article": "Article 7",
        "title": "Amendments to Annex III",
        "text": (
            "The Commission is empowered to adopt delegated acts to amend Annex III by adding or modifying use-cases "
            "of high-risk AI systems where an AI system poses a risk of harm to health, safety, or fundamental rights "
            "that is equivalent to, or greater than, the risk of harm posed by the high-risk AI systems already "
            "referred to in Annex III. When assessing the condition, the Commission shall consider criteria such as "
            "the intended purpose, the extent of use, the nature and amount of data processed, the degree of autonomy, "
            "and the reversibility of harms."
        ),
    },
    {
        "id": "art_8",
        "article": "Article 8",
        "title": "Compliance with the requirements",
        "text": (
            "High-risk AI systems shall comply with the requirements laid down in Chapter III Section 2 (Articles 9-15), "
            "taking into account their intended purpose and the generally acknowledged state of the art. The risk "
            "management system, data governance, technical documentation, record-keeping, transparency, human oversight, "
            "and accuracy and robustness requirements must all be satisfied. The provider's quality management system "
            "shall take those requirements into account."
        ),
    },
    {
        "id": "art_9",
        "article": "Article 9",
        "title": "Risk management system",
        "text": (
            "A risk management system shall be established, implemented, documented and maintained in relation to "
            "high-risk AI systems. It shall be a continuous iterative process planned and run throughout the entire "
            "lifecycle of a high-risk AI system, requiring regular systematic review and updating. The risk management "
            "system shall include: (a) identification and analysis of known and reasonably foreseeable risks that the "
            "high-risk AI system can pose to health, safety or fundamental rights; (b) estimation and evaluation of "
            "the risks that may emerge when the system is used in accordance with its intended purpose and under "
            "conditions of reasonably foreseeable misuse; (c) evaluation of other risks possibly arising based on "
            "post-market monitoring data; (d) adoption of appropriate and targeted risk management measures designed "
            "to address the identified risks. Residual risks shall be communicated to the deployer. Testing shall be "
            "performed to identify the most appropriate risk management measures. Testing shall be suitable to the "
            "intended purpose and shall be performed prior to placing on the market or putting into service."
        ),
    },
    {
        "id": "art_10",
        "article": "Article 10",
        "title": "Data and data governance",
        "text": (
            "High-risk AI systems which make use of techniques involving the training of AI models with data shall "
            "be developed on the basis of training, validation and testing data sets that meet the quality criteria "
            "referred to in this Article. Training, validation and testing data sets shall be subject to data "
            "governance and management practices appropriate for the intended purpose of the high-risk AI system. "
            "Those practices shall concern in particular: (a) the relevant design choices; (b) data collection "
            "processes and the origin of data, and in the case of personal data, the original purpose of the data "
            "collection; (c) relevant data-preparation processing operations, such as annotation, labelling, "
            "cleaning, updating, enrichment and aggregation; (d) the formulation of assumptions, in particular with "
            "respect to the information that the data are supposed to measure and represent; (e) an assessment of "
            "the availability, quantity and suitability of the data sets needed; (f) examination in view of possible "
            "biases that are likely to affect the health and safety of persons, have a negative impact on fundamental "
            "rights, or lead to discrimination prohibited under Union law; (g) appropriate measures to detect, "
            "prevent and mitigate possible biases; (h) the identification of relevant data gaps or shortcomings and "
            "how they can be addressed. Training, validation and testing data sets shall be relevant, sufficiently "
            "representative, and to the best extent possible, free of errors and complete in view of the intended purpose."
        ),
    },
    {
        "id": "art_11",
        "article": "Article 11",
        "title": "Technical documentation",
        "text": (
            "The technical documentation of a high-risk AI system shall be drawn up before that system is placed on "
            "the market or put into service and shall be kept up-to-date. The technical documentation shall be drawn "
            "up in such a way as to demonstrate that the high-risk AI system complies with the requirements set out "
            "in this Section and to provide national competent authorities and notified bodies with all the necessary "
            "information in a clear and comprehensive form to assess compliance. It shall contain, at a minimum, the "
            "elements set out in Annex IV: a general description, detailed description of elements and development "
            "process, monitoring and functioning information, and risk management documentation."
        ),
    },
    {
        "id": "art_12",
        "article": "Article 12",
        "title": "Record-keeping",
        "text": (
            "High-risk AI systems shall technically allow for the automatic recording of events (logs) over the "
            "lifetime of the system. The logging capabilities shall ensure a level of traceability of the AI system's "
            "functioning throughout its lifecycle that is appropriate to the intended purpose of the system. In "
            "particular, the logging capabilities shall enable the monitoring of the operation of the high-risk AI "
            "system with respect to the occurrence of situations that may result in the AI system presenting a risk "
            "within the meaning of Article 79(1) or lead to a substantial modification, and facilitate the "
            "post-market monitoring referred to in Article 72. For high-risk AI systems referred to in Annex III "
            "point 1(a), the logging capabilities shall provide, at a minimum, the following: (a) recording of the "
            "period of each use of the system; (b) the reference database against which input data has been checked; "
            "(c) the input data for which the search has led to a match; (d) the identification of the natural "
            "persons involved in the verification of the results. Logs shall be kept for a period appropriate to the "
            "intended purpose and applicable legal obligations, for at least six months."
        ),
    },
    {
        "id": "art_13",
        "article": "Article 13",
        "title": "Transparency and provision of information to deployers",
        "text": (
            "High-risk AI systems shall be designed and developed in such a way as to ensure that their operation is "
            "sufficiently transparent to enable deployers to interpret a system's output and use it appropriately. "
            "An appropriate type and degree of transparency shall be ensured, with a view to achieving compliance "
            "with the relevant obligations of the provider and deployer. High-risk AI systems shall be accompanied "
            "by instructions for use in an appropriate digital format or otherwise that include concise, complete, "
            "correct and clear information that is relevant, accessible and comprehensible to deployers, including: "
            "(a) the identity and contact details of the provider; (b) the characteristics, capabilities and "
            "limitations of performance of the high-risk AI system, including its intended purpose, the level of "
            "accuracy, robustness and cybersecurity, any known or foreseeable circumstance that may lead to risks, "
            "and the specifications for input data; (c) any changes to the system previously determined by the "
            "provider at the moment of initial conformity assessment; (d) the human oversight measures, including "
            "the technical measures put in place to facilitate interpretation of outputs; (e) the computational and "
            "hardware resources needed; (f) any relevant history of known performance issues."
        ),
    },
    {
        "id": "art_14",
        "article": "Article 14",
        "title": "Human oversight",
        "text": (
            "High-risk AI systems shall be designed and developed in such a way, including with appropriate "
            "human-machine interface tools, that they can be effectively overseen by natural persons during the "
            "period in which they are in use. Human oversight shall aim at minimising the risks to health, safety "
            "or fundamental rights that may emerge when a high-risk AI system is used in accordance with its "
            "intended purpose or under conditions of reasonably foreseeable misuse, in particular where such risks "
            "persist despite the application of other requirements. Human oversight measures shall be commensurate "
            "with the risks, level of autonomy and context of use of the high-risk AI system, and shall be ensured "
            "through either or both of the following types of measures: (a) measures identified and built, when "
            "technically feasible, into the high-risk AI system by the provider before it is placed on the market "
            "or put into service; (b) measures identified by the provider before placing the high-risk AI system "
            "on the market or putting it into service and that are appropriate to be implemented by the deployer. "
            "The individuals to whom human oversight is assigned shall be enabled to: (a) properly understand the "
            "relevant capacities and limitations of the high-risk AI system and be able to duly monitor its "
            "operation; (b) remain aware of the possible tendency of automatically relying or over-relying on the "
            "output produced by a high-risk AI system (automation bias); (c) correctly interpret the high-risk AI "
            "system's output; (d) decide, in any particular situation, not to use the high-risk AI system or to "
            "disregard, override or reverse the output of the high-risk AI system; (e) intervene in the operation "
            "of the high-risk AI system or interrupt the system through a 'stop' button or a similar procedure "
            "that allows the system to come to a halt in a safe state. For high-risk AI systems referred to in "
            "Annex III point 1(a), the human oversight measures shall, in addition, ensure that no action or "
            "decision is taken by the deployer on the basis of the identification resulting from the system unless "
            "this has been separately verified and confirmed by at least two natural persons."
        ),
    },
    {
        "id": "art_15",
        "article": "Article 15",
        "title": "Accuracy, robustness and cybersecurity",
        "text": (
            "High-risk AI systems shall be designed and developed in such a way that they achieve an appropriate "
            "level of accuracy, robustness, and cybersecurity, and that they perform consistently in those respects "
            "throughout their lifecycle. The levels of accuracy and the relevant accuracy metrics of high-risk AI "
            "systems shall be declared in the accompanying instructions of use. The levels of accuracy shall be "
            "appropriate to the intended purpose. High-risk AI systems shall be as resilient as possible regarding "
            "errors, faults or inconsistencies that may occur within the system or the environment in which the "
            "system operates, in particular due to their interaction with natural persons or other systems. "
            "Technical and organisational measures shall be taken to ensure that the accuracy and cybersecurity of "
            "high-risk AI systems are robust against attempts by unauthorised third parties to alter their use, "
            "outputs or performance by exploiting system vulnerabilities. The technical solutions to address AI "
            "specific vulnerabilities shall include, where appropriate, measures to prevent, detect, respond to, "
            "resolve and control for attacks trying to manipulate the training data set (data poisoning), or "
            "pre-trained components used in training (model poisoning), inputs designed to cause the AI model to "
            "make a mistake (adversarial examples or model evasion), confidentiality attacks or model flaws."
        ),
    },
    # ===== OBLIGATIONS OF PROVIDERS AND DEPLOYERS =====
    {
        "id": "art_16",
        "article": "Article 16",
        "title": "Obligations of providers of high-risk AI systems",
        "text": (
            "Providers of high-risk AI systems shall: (a) ensure that their high-risk AI systems are compliant with "
            "the requirements set out in Chapter III Section 2; (b) indicate on the high-risk AI system or, where "
            "not possible, on its packaging or documentation, their name, registered trade name or trademark, the "
            "address at which they can be contacted; (c) have a quality management system in place which complies "
            "with Article 17; (d) keep the documentation referred to in Article 18; (e) keep the logs automatically "
            "generated by their systems when under their control; (f) ensure that the system undergoes the relevant "
            "conformity assessment procedure; (g) draw up an EU declaration of conformity; (h) affix the CE marking; "
            "(i) upon reasoned request by a national competent authority, demonstrate the conformity of the system; "
            "(j) ensure that the system complies with accessibility requirements."
        ),
    },
    {
        "id": "art_17",
        "article": "Article 17",
        "title": "Quality management system",
        "text": (
            "Providers of high-risk AI systems shall put a quality management system in place that ensures compliance "
            "with this Regulation. That quality management system shall be documented in a systematic and orderly "
            "manner in the form of written policies, procedures and instructions, and shall include at least: "
            "(a) a strategy for regulatory compliance; (b) techniques, procedures and systematic actions to be used "
            "for the design, design control and design verification; (c) techniques, procedures and systematic "
            "actions to be used for the development, quality control and quality assurance; (d) examination, test "
            "and validation procedures to be carried out before, during and after development; (e) technical "
            "specifications to be applied; (f) systems and procedures for data management, including data "
            "collection, analysis, labelling, storage, filtration, mining, aggregation, retention and any other "
            "operation regarding the data carried out before and for the purpose of the placing on the market; "
            "(g) the risk management system referred to in Article 9; (h) the setting-up, implementation and "
            "maintenance of a post-market monitoring system; (i) procedures related to the reporting of a serious "
            "incident; (j) the handling of communication with national competent authorities, other relevant "
            "authorities, notified bodies, other operators, customers or other interested parties; (k) systems and "
            "procedures for record keeping; (l) resource management, including supply-chain related measures; "
            "(m) an accountability framework."
        ),
    },
    {
        "id": "art_26",
        "article": "Article 26",
        "title": "Obligations of deployers of high-risk AI systems",
        "text": (
            "Deployers of high-risk AI systems shall: (a) take appropriate technical and organisational measures to "
            "ensure they use such systems in accordance with the instructions of use accompanying the systems; "
            "(b) assign human oversight to natural persons who have the necessary competence, training and authority; "
            "(c) to the extent they exercise control over the input data, ensure that input data is relevant and "
            "sufficiently representative in view of the intended purpose; (d) monitor the operation of the high-risk "
            "AI system on the basis of the instructions of use and inform the provider where appropriate; (e) keep "
            "the logs automatically generated by the system, to the extent such logs are under their control, for at "
            "least six months; (f) use the information provided under Article 13 to comply with their obligation to "
            "carry out a data protection impact assessment under Article 35 of Regulation (EU) 2016/679; (g) "
            "cooperate with the relevant competent authorities; (h) where they are public authorities or Union "
            "institutions, carry out a fundamental rights impact assessment."
        ),
    },
    {
        "id": "art_27",
        "article": "Article 27",
        "title": "Fundamental rights impact assessment for high-risk AI systems",
        "text": (
            "Before putting into use a high-risk AI system as referred to in Article 6(2), deployers that are bodies "
            "governed by public law, or private entities providing public services, and deployers of high-risk AI "
            "systems referred to in Annex III points 5(b) and 5(c) shall perform an assessment of the impact on "
            "fundamental rights that the use of such system may produce. The assessment shall include: (a) a "
            "description of the deployer's processes in which the high-risk AI system will be used; (b) a description "
            "of the period and frequency of use; (c) the categories of natural persons and groups likely to be "
            "affected; (d) the specific risks of harm likely to affect those categories; (e) a description of the "
            "implementation of human oversight measures; (f) the measures to be taken in the case of materialisation "
            "of those risks."
        ),
    },
    # ===== TITLE IV – TRANSPARENCY OBLIGATIONS =====
    {
        "id": "art_50",
        "article": "Article 50",
        "title": "Transparency obligations for providers and deployers of certain AI systems",
        "text": (
            "Providers shall ensure that AI systems intended to interact directly with natural persons are designed "
            "and developed in such a way that the natural persons concerned are informed that they are interacting "
            "with an AI system, unless this is obvious from the point of view of a natural person who is reasonably "
            "well-informed, observant and circumspect, taking into account the circumstances and the context of use. "
            "Providers of AI systems, including general-purpose AI systems, generating synthetic audio, image, video "
            "or text content, shall ensure that the outputs of the AI system are marked in a machine-readable format "
            "and detectable as artificially generated or manipulated. Deployers of an emotion recognition system or "
            "a biometric categorisation system shall inform the natural persons exposed thereto of the operation of "
            "the system, and shall process the personal data in accordance with Regulation (EU) 2016/679. Deployers "
            "of an AI system that generates or manipulates image, audio or video content constituting a deep fake, "
            "shall disclose that the content has been artificially generated or manipulated. Deployers of an AI "
            "system that generates or manipulates text which is published with the purpose of informing the public "
            "on matters of public interest shall disclose that the text has been artificially generated or manipulated."
        ),
    },
    # ===== TITLE V – GENERAL-PURPOSE AI MODELS =====
    {
        "id": "art_51",
        "article": "Article 51",
        "title": "Classification of general-purpose AI models as with systemic risk",
        "text": (
            "A general-purpose AI model shall be classified as a general-purpose AI model with systemic risk if it "
            "meets any of the following conditions: (a) it has high impact capabilities evaluated on the basis of "
            "appropriate technical tools and methodologies, including indicators and benchmarks; (b) based on a "
            "decision of the Commission, having regard to criteria set out in Annex XIII, it has capabilities or an "
            "impact equivalent to those of general-purpose AI models meeting the criterion in point (a). A "
            "general-purpose AI model shall be presumed to have high impact capabilities when the cumulative amount "
            "of compute used for its training measured in floating point operations is greater than 10^25."
        ),
    },
    {
        "id": "art_53",
        "article": "Article 53",
        "title": "Obligations for providers of general-purpose AI models",
        "text": (
            "Providers of general-purpose AI models shall: (a) draw up and keep up-to-date the technical "
            "documentation of the model, including its training and testing process and the results of its "
            "evaluation, which shall contain, at a minimum, the information set out in Annex XI; (b) draw up, keep "
            "up-to-date and make available information and documentation to providers of AI systems who intend to "
            "integrate the general-purpose AI model into their AI system; (c) put in place a policy to comply with "
            "Union law on copyright and related rights; (d) draw up and make publicly available a sufficiently "
            "detailed summary about the content used for training of the general-purpose AI model, according to a "
            "template provided by the AI Office."
        ),
    },
    {
        "id": "art_55",
        "article": "Article 55",
        "title": "Obligations for providers of general-purpose AI models with systemic risk",
        "text": (
            "In addition to the obligations listed in Article 53, providers of general-purpose AI models with "
            "systemic risk shall: (a) perform model evaluation in accordance with standardised protocols and tools "
            "reflecting the state of the art, including conducting and documenting adversarial testing of the model "
            "with a view to identifying and mitigating systemic risk; (b) assess and mitigate possible systemic "
            "risks, including their sources, that may stem from the development, the placing on the market, or the "
            "use of general-purpose AI models with systemic risk; (c) keep track of, document, and report to the AI "
            "Office and, as appropriate, to national competent authorities, relevant information about serious "
            "incidents and possible corrective measures to address them; (d) ensure an adequate level of cybersecurity "
            "protection for the general-purpose AI model with systemic risk and the physical infrastructure of the "
            "model."
        ),
    },
    # ===== ANNEX III – HIGH-RISK USE CASES =====
    {
        "id": "annex_iii_1",
        "article": "Annex III, Point 1",
        "title": "Biometrics (High-Risk)",
        "text": (
            "AI systems intended to be used for biometric identification and categorisation of natural persons: "
            "(a) AI systems intended to be used for the 'real-time' and 'post' remote biometric identification of "
            "natural persons. Biometric-based AI systems used for verification (one-to-one matching) for the sole "
            "purpose of confirming that a specific natural person is the person they claim to be are excluded from "
            "high-risk classification."
        ),
    },
    {
        "id": "annex_iii_2",
        "article": "Annex III, Point 2",
        "title": "Critical infrastructure (High-Risk)",
        "text": (
            "AI systems intended to be used as safety components in the management and operation of critical digital "
            "infrastructure, road traffic, or in the supply of water, gas, heating or electricity. This includes "
            "AI systems used in the management and operation of critical infrastructure such as transport networks, "
            "utilities, and digital infrastructure where failure could endanger health, safety, or cause significant "
            "economic disruption."
        ),
    },
    {
        "id": "annex_iii_3",
        "article": "Annex III, Point 3",
        "title": "Education and vocational training (High-Risk)",
        "text": (
            "AI systems intended to be used for: (a) determining access or admission to educational and vocational "
            "training institutions at all levels; (b) evaluating learning outcomes, including those used to steer "
            "the learning process; (c) determining the level of education that an individual will receive or be "
            "able to access; (d) monitoring and detecting prohibited behaviour of students during tests. These "
            "systems are high-risk because they can determine the educational and professional course of a person's "
            "life and therefore their ability to secure their livelihood."
        ),
    },
    {
        "id": "annex_iii_4",
        "article": "Annex III, Point 4",
        "title": "Employment, workers management and access to self-employment (High-Risk)",
        "text": (
            "AI systems intended to be used for: (a) recruitment or selection of natural persons, in particular to "
            "place targeted job advertisements, to analyse and filter job applications, and to evaluate candidates; "
            "(b) making decisions affecting terms of work-related relationships, the promotion or termination of "
            "work-related contractual relationships, to allocate tasks based on individual behaviour or personal "
            "traits or characteristics, or to monitor and evaluate the performance and behaviour of persons in such "
            "relationships. These are classified as high-risk because such systems may appreciably impact future "
            "career prospects, livelihoods and workers' rights."
        ),
    },
    {
        "id": "annex_iii_5",
        "article": "Annex III, Point 5",
        "title": "Access to essential services (High-Risk)",
        "text": (
            "AI systems intended to be used for: (a) evaluating the eligibility of natural persons for essential "
            "public assistance benefits and services, including healthcare services, and for granting, reducing, "
            "revoking, or reclaiming such benefits and services; (b) evaluating the creditworthiness of natural "
            "persons or establishing their credit score, with the exception of AI systems used for the purpose of "
            "detecting financial fraud; (c) risk assessment and pricing in relation to natural persons in the case "
            "of life and health insurance; (d) evaluating and classifying emergency calls by natural persons or "
            "for dispatching or establishing priority in emergency first response services."
        ),
    },
    {
        "id": "annex_iii_6",
        "article": "Annex III, Point 6",
        "title": "Law enforcement (High-Risk)",
        "text": (
            "AI systems intended to be used by or on behalf of law enforcement authorities for: (a) individual risk "
            "assessments of natural persons to assess the risk of a natural person committing criminal offences or "
            "reoffending; (b) polygraphs and similar tools; (c) evaluation of the reliability of evidence in the "
            "course of investigation or prosecution of criminal offences; (d) assessment of the risk of a natural "
            "person becoming the victim of criminal offences; (e) profiling of natural persons in the course of "
            "detection, investigation or prosecution of criminal offences."
        ),
    },
    {
        "id": "annex_iii_7",
        "article": "Annex III, Point 7",
        "title": "Migration, asylum and border control management (High-Risk)",
        "text": (
            "AI systems intended to be used by or on behalf of competent public authorities or by United Nations "
            "agencies as: (a) polygraphs and similar tools; (b) assessment of a risk, including a security risk, "
            "a risk of irregular immigration, or a health risk, posed by a natural person who intends to enter or "
            "has entered the territory of a Member State; (c) to assist competent public authorities in the "
            "examination of applications for asylum, visa, and residence permits and associated complaints with "
            "regard to the eligibility of the natural persons applying for a status; (d) for the purpose of "
            "detection, recognition or identification of natural persons in the context of migration, asylum and "
            "border control management."
        ),
    },
    {
        "id": "annex_iii_8",
        "article": "Annex III, Point 8",
        "title": "Administration of justice and democratic processes (High-Risk)",
        "text": (
            "AI systems intended to be used by judicial authorities or on their behalf to assist in researching "
            "and interpreting facts and the law and in applying the law to a concrete set of facts, or to be used "
            "in a similar way in alternative dispute resolution. AI systems intended to be used for influencing the "
            "outcome of an election or referendum or the voting behaviour of natural persons in the exercise of "
            "their vote in elections or referenda. This does not include AI systems the output of which does not "
            "directly interact with natural persons, such as tools used to organise, optimise or structure "
            "political campaigns from an administrative and logistic point of view."
        ),
    },
    # ===== ENFORCEMENT AND GOVERNANCE =====
    {
        "id": "art_64",
        "article": "Article 64",
        "title": "AI Office",
        "text": (
            "An AI Office is established within the Commission. The AI Office shall carry out its tasks and exercise "
            "its powers independently and impartially. It shall not seek or take instructions from any Union "
            "institution, body, office or agency, any government of a Member State or any other public or private "
            "body. The AI Office shall contribute to the implementation of, and monitoring compliance with, this "
            "Regulation. It shall carry out advisory, coordination and supervisory tasks for the purposes of this "
            "Regulation, and serve as a centre of expertise across the Union."
        ),
    },
    {
        "id": "art_72",
        "article": "Article 72",
        "title": "Post-market monitoring by providers and post-market monitoring plan for high-risk AI systems",
        "text": (
            "Providers shall establish and document a post-market monitoring system in a manner that is proportionate "
            "to the nature of the AI technologies and the risks of the high-risk AI system. The post-market monitoring "
            "system shall actively and systematically collect, document and analyse relevant data which may be "
            "provided by deployers or which may be collected through other sources on the performance of high-risk AI "
            "systems throughout their lifetime, and which allow the provider to evaluate the continuous compliance of "
            "AI systems with the requirements. The post-market monitoring system shall be based on a post-market "
            "monitoring plan. The plan shall comprise at least: (a) data collection and analysis strategy; "
            "(b) description of complaints handling; (c) corrective action strategy; (d) regular reporting obligations."
        ),
    },
    # ===== PENALTIES =====
    {
        "id": "art_99",
        "article": "Article 99",
        "title": "Penalties",
        "text": (
            "Infringements of the prohibition of AI practices referred to in Article 5 shall be subject to "
            "administrative fines of up to EUR 35,000,000 or, if the offender is an undertaking, up to 7% of its "
            "total worldwide annual turnover for the preceding financial year, whichever is higher. Non-compliance "
            "with any of the requirements or obligations under this Regulation, other than those laid down in "
            "Article 5, shall be subject to administrative fines of up to EUR 15,000,000 or, if the offender is "
            "an undertaking, up to 3% of its total worldwide annual turnover. The supply of incorrect, incomplete "
            "or misleading information to notified bodies or national competent authorities shall be subject to "
            "administrative fines of up to EUR 7,500,000 or, if the offender is an undertaking, up to 1% of its "
            "total worldwide annual turnover."
        ),
    },
    # ===== CONFORMITY ASSESSMENT =====
    {
        "id": "art_43",
        "article": "Article 43",
        "title": "Conformity assessment",
        "text": (
            "For high-risk AI systems listed in Annex III, the provider shall follow either the conformity "
            "assessment procedure based on internal control referred to in Annex VI, or the conformity assessment "
            "procedure based on assessment of the quality management system and technical documentation with the "
            "involvement of a notified body referred to in Annex VII. Where the provider demonstrates to the "
            "notified body that they have applied harmonised standards or common specifications, the need for "
            "specific checks may be reduced. For biometric identification systems (Annex III point 1), the "
            "conformity assessment based on internal control (Annex VI) is not available — a notified body must "
            "be involved."
        ),
    },
    {
        "id": "art_47",
        "article": "Article 47",
        "title": "EU declaration of conformity",
        "text": (
            "The provider shall draw up a written or digitally signed EU declaration of conformity for each "
            "high-risk AI system, and keep it at the disposal of the national competent authorities for 10 years "
            "after the AI system has been placed on the market or put into service. The EU declaration of conformity "
            "shall identify the AI system for which it has been drawn up. It shall state that the high-risk AI "
            "system in question is in conformity with the requirements set out in Chapter III Section 2 and, where "
            "applicable, any relevant other Union legislation, and that the appropriate conformity assessment "
            "procedures have been applied."
        ),
    },
    {
        "id": "art_49",
        "article": "Article 49",
        "title": "Registration",
        "text": (
            "Before placing on the market or putting into service a high-risk AI system listed in Annex III, the "
            "provider or, where applicable, the authorised representative shall register themselves and the system "
            "in the EU database referred to in Article 71. Providers of AI systems that consider they are not "
            "high-risk per the derogation in Article 6(3) shall also register in that database. Deployers of "
            "high-risk AI systems that are public authorities or act on behalf of public authorities shall register "
            "in the EU database as well."
        ),
    },
    # ===== TIMELINE AND ENTRY INTO FORCE =====
    {
        "id": "art_113",
        "article": "Article 113",
        "title": "Entry into force and application",
        "text": (
            "This Regulation enters into force on the twentieth day following its publication in the Official Journal "
            "of the European Union (1 August 2024). The following application timeline applies:\n"
            "- Prohibited practices (Title II): From 2 February 2025\n"
            "- General-purpose AI models (Title V), governance (Title VII Chapters 1-2), penalties: From 2 August 2025\n"
            "- High-risk systems that are products under Annex I, and obligations for notified bodies: From 2 August 2025\n"
            "- High-risk AI requirements (Title III Chapter III Section 2), obligations of operators, transparency (Title IV): From 2 August 2026\n"
            "- Certain high-risk systems listed in Annex III used by public authorities: From 2 August 2027\n"
            "This Regulation shall be binding in its entirety and directly applicable in all Member States."
        ),
    },
]


def ingest():
    """Write EU AI Act articles to a JSON file for the TF-IDF retrieval engine."""
    print(f"Output path: {ARTICLES_PATH}")

    # Write articles as JSON
    with open(ARTICLES_PATH, "w", encoding="utf-8") as f:
        json.dump(EU_AI_ACT_ARTICLES, f, indent=2, ensure_ascii=False)

    print(f"Ingested {len(EU_AI_ACT_ARTICLES)} articles to {ARTICLES_PATH}")

    # Quick sanity check using the vector store search
    from core.vector_store import query_articles, query_by_topic

    # Force reload
    import core.vector_store as vs
    vs._articles = None
    vs._tfidf_matrix = None
    vs._idf = None

    print("\nSanity check — query: 'human oversight of AI systems'")
    results = query_articles("human oversight of AI systems", n_results=3)
    for i, r in enumerate(results):
        print(f"  {i+1}. [{r['article']}] {r['title']}  (score={r['score']:.4f})")

    print("\nSanity check — topic: 'data_governance'")
    context = query_by_topic("data_governance", n_results=2)
    print(f"  Context length: {len(context)} chars")
    print(f"  Preview: {context[:200]}...")

    print("\nSanity check — query: 'social scoring prohibited'")
    results = query_articles("social scoring prohibited", n_results=3)
    for i, r in enumerate(results):
        print(f"  {i+1}. [{r['article']}] {r['title']}  (score={r['score']:.4f})")

    print("\nIngestion complete!")


if __name__ == "__main__":
    ingest()
