#!/usr/bin/env python3
"""Batch Statutory Law Ingestion Script for CLO Agent Knowledge Base."""

import json
import urllib.request
import time

ALB_URL = "http://cloagent-alb-896741255.ap-south-1.elb.amazonaws.com"

MAJOR_LAWS = [
    {
        "doc_id": "us-sec-iaa-1940-sec206",
        "title": "US Investment Advisers Act of 1940 - Section 206 Fiduciary Duty & Investment Advice",
        "content": (
            "Section 206 of the Investment Advisers Act of 1940 makes it unlawful for any investment adviser "
            "to employ any device, scheme, or artifice to defraud any client or prospective client, or to engage "
            "in any transaction, practice, or course of business which operates as a fraud or deceit upon any client. "
            "Under SEC regulations and FINRA Rule 2210, automated systems or artificial intelligence algorithms that generate "
            "personalized investment recommendations or financial advice to retail clients are deemed investment advisers, "
            "triggering mandatory SEC/state registration, fiduciary duties of care and loyalty, suitability requirements, "
            "and strict supervisory recordkeeping rules."
        ),
        "doc_type": "ACT",
        "issuing_authority": "US Securities and Exchange Commission (SEC)",
        "jurisdiction": "US-FEDERAL",
        "effective_date": "1940-08-22"
    },
    {
        "doc_id": "us-ftc-act-sec5-udap",
        "title": "US Federal Trade Commission Act - Section 5 Unfair or Deceptive Acts or Practices (UDAP)",
        "content": (
            "Section 5 of the Federal Trade Commission (FTC) Act prohibits unfair or deceptive acts or practices in or affecting commerce. "
            "FTC guidance on Artificial Intelligence and Automated Decision-Making mandates that companies deploying AI tools "
            "for financial guidance, consumer credit, or customer interactions must ensure outputs are accurate, non-deceptive, "
            "and supported by empirical evidence. Generating automated, hallucinated, or unhedged financial advice that results "
            "in consumer financial loss constitutes an actionable deceptive trade practice subject to FTC enforcement and civil penalties."
        ),
        "doc_type": "ACT",
        "issuing_authority": "US Federal Trade Commission (FTC)",
        "jurisdiction": "US-FEDERAL",
        "effective_date": "1914-09-26"
    },
    {
        "doc_id": "us-glba-safeguards-rule",
        "title": "Gramm-Leach-Bliley Act (GLBA) Financial Privacy & Safeguards Rule",
        "content": (
            "The Gramm-Leach-Bliley Act (GLBA) Privacy Rule and FTC Safeguards Rule mandate that financial institutions "
            "protect nonpublic personal information (NPI) of consumers. Processing customer support chat logs containing financial records "
            "or payment data requires clear privacy notices, consumer opt-out mechanisms before sharing NPI with third-party AI vendors, "
            "strict administrative, technical, and physical safeguards, and comprehensive vendor risk management controls."
        ),
        "doc_type": "REGULATION",
        "issuing_authority": "Federal Trade Commission & Consumer Financial Protection Bureau (CFPB)",
        "jurisdiction": "US-FEDERAL",
        "effective_date": "1999-11-12"
    },
    {
        "doc_id": "us-ny-crl-sec52c-employee-monitoring",
        "title": "New York Civil Rights Law Section 52-c - Electronic Monitoring Notice",
        "content": (
            "New York Civil Rights Law Section 52-c requires any private employer who monitors or intercepts employee telephone "
            "conversations, email, or internet access/usage on any electronic device or system to give prior written notice "
            "upon hiring to all employees subject to monitoring. Employers must post a conspicuous notice of electronic monitoring "
            "in the workplace and obtain written or electronic acknowledgment from new hires before monitoring commences."
        ),
        "doc_type": "ACT",
        "issuing_authority": "State of New York Legislature",
        "jurisdiction": "US-NY",
        "effective_date": "2022-05-07"
    },
    {
        "doc_id": "us-ca-cpra-employee-privacy",
        "title": "California Privacy Rights Act (CPRA / CCPA) Employee Privacy Rights",
        "content": (
            "Under the California Consumer Privacy Act (CCPA) as amended by the California Privacy Rights Act (CPRA), "
            "California employees have full consumer privacy rights regarding employment-related personal information. "
            "Employers installing employee activity monitoring software must issue a Notice at Collection specifying the categories "
            "of personal and sensitive personal information collected (e.g., keystrokes, screen captures, web history), the operational purposes, "
            "and retention periods. Employees have the right to know, correct, limit use of sensitive personal information, and request deletion."
        ),
        "doc_type": "ACT",
        "issuing_authority": "California Privacy Protection Agency (CPPA)",
        "jurisdiction": "US-CA",
        "effective_date": "2023-01-01"
    },
    {
        "doc_id": "eu-gdpr-art88-employment-monitoring",
        "title": "EU General Data Protection Regulation (GDPR) - Article 88 Employment Processing & Monitoring",
        "content": (
            "Article 88 of the General Data Protection Regulation (GDPR) permits Member States to provide specific rules for processing "
            "employees' personal data in the employment context. Employers implementing employee monitoring tools must demonstrate a valid lawful basis "
            "under Article 6 (such as legitimate interest under Article 6(1)(f), balanced against employee fundamental privacy rights under Article 8 of the EU Charter). "
            "Employee consent is generally invalid due to employment power imbalance. Continuous keystroke logging or screen recording violates data minimization (Article 5(1)(c)) "
            "and requires prior Data Protection Impact Assessment (DPIA) under Article 35 and works council co-determination in jurisdictions such as Germany and the Netherlands."
        ),
        "doc_type": "REGULATION",
        "issuing_authority": "European Parliament and Council of the European Union",
        "jurisdiction": "EU",
        "effective_date": "2018-05-25"
    },
    {
        "doc_id": "eu-ai-act-art6-high-risk",
        "title": "European Union Artificial Intelligence Act (EU AI Act) - High-Risk AI Systems",
        "content": (
            "The EU AI Act classifies AI systems intended to be used for employment, worker management, access to self-employment, "
            "or financial risk assessment and credit scoring as High-Risk AI Systems under Annex III. Operators deploying High-Risk AI "
            "must conduct fundamental rights impact assessments, implement risk management systems, maintain human oversight mechanisms, "
            "ensure technical transparency, and provide clear worker notifications before deployment."
        ),
        "doc_type": "REGULATION",
        "issuing_authority": "European Union Artificial Intelligence Office",
        "jurisdiction": "EU",
        "effective_date": "2024-08-01"
    },
    {
        "doc_id": "in-dpdp-act-2023-sec6-consent",
        "title": "Digital Personal Data Protection Act 2023 (India) - Section 6 Notice & Consent Rules",
        "content": (
            "Section 6 of India's Digital Personal Data Protection Act (DPDP Act) 2023 requires every request for consent to be preceded or "
            "accompanied by an itemised notice in clear and plain language. The notice must specify the personal data sought to be processed, "
            "the explicit purpose of processing, the manner in which the data principal may exercise rights, and details of the Data Protection Officer. "
            "For employee monitoring or AI data processing, data fiduciaries must provide clear statutory notice and maintain proof of consent or legitimate employment processing compliance."
        ),
        "doc_type": "ACT",
        "issuing_authority": "Ministry of Electronics and Information Technology (MeitY)",
        "jurisdiction": "central",
        "effective_date": "2023-08-11"
    }
]

def ingest_law(law: dict):
    url = f"{ALB_URL}/mcp/tools/ingest_document/call"
    body = json.dumps(law).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[OK] Ingested {law['doc_id']}: {law['title']} -> {data.get('success')}")
    except Exception as e:
        print(f"[ERR] Failed {law['doc_id']}: {e}")

def main():
    print(f"Starting batch statutory law ingestion ({len(MAJOR_LAWS)} major laws)...")
    for law in MAJOR_LAWS:
        ingest_law(law)
        time.sleep(1)
    print("Ingestion complete!")

if __name__ == "__main__":
    main()
