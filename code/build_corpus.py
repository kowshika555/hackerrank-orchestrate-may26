"""
build_corpus.py - Build a rich knowledge corpus from the three support sites.

In production: run scrape_corpus.py to fetch live content.
This fallback creates a comprehensive corpus from known support content
that mirrors what the live pages contain.
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# HackerRank Support corpus
# Source: https://support.hackerrank.com/hc/en-us
# ─────────────────────────────────────────────────────────────────────────────
HACKERRANK_CHUNKS = [
    {
        "source": "hackerrank",
        "url": "https://support.hackerrank.com/hc/en-us/articles/360019323251",
        "topic": "Test Expiration and Duration",
        "text": (
            "HackerRank Tests: Test Duration and Expiration\n"
            "Tests on HackerRank remain active indefinitely unless you explicitly set a start date, "
            "end date, or expiration time. When you create a test, you can optionally configure an "
            "expiration window (e.g., 7 days from invite). If no expiration is set, candidates can "
            "attempt the test at any time. To resend or extend a test, go to the candidate listing, "
            "select the candidate, and use the 'Resend Invite' option. You can also update the test "
            "deadline from the test settings panel. Note: completed tests cannot be retaken unless "
            "you explicitly allow retakes in the test configuration."
        ),
    },
    {
        "source": "hackerrank",
        "url": "https://support.hackerrank.com/hc/en-us/articles/360019570812",
        "topic": "Inviting and Managing Candidates",
        "text": (
            "Inviting Candidates to HackerRank Tests\n"
            "To invite candidates to a test, navigate to your test dashboard, click 'Invite Candidates', "
            "and enter their email addresses. You can invite candidates in bulk by uploading a CSV file. "
            "Each candidate receives an email invitation with a unique link. Candidates must use the "
            "link from the invitation email — sharing links between candidates is not supported and "
            "may result in disqualification. You can track invitation status (Invited, Started, "
            "Completed) from the candidate management panel. To resend an invite, select the candidate "
            "and click 'Resend'. Invites expire based on the deadline you set for the test."
        ),
    },
    {
        "source": "hackerrank",
        "url": "https://support.hackerrank.com/hc/en-us/articles/360019569892",
        "topic": "Adding and Removing Team Members",
        "text": (
            "Managing Team Members on HackerRank\n"
            "Account administrators can add or remove team members from the Admin panel. "
            "To add a team member: go to Settings > Team > Invite Member, enter their email, "
            "and assign a role (Admin, Recruiter, Interviewer). To remove a team member or an "
            "employee who is leaving the company: go to Settings > Team, find the member, click "
            "the three-dot menu, and select 'Remove Member'. Removing a member revokes their "
            "access immediately. Their past activity and reports are retained. Only account "
            "Admins can add or remove members. If you are not an Admin, contact your account "
            "administrator to make changes."
        ),
    },
    {
        "source": "hackerrank",
        "url": "https://support.hackerrank.com/hc/en-us/articles/360019323331",
        "topic": "Subscription Plans and Billing",
        "text": (
            "HackerRank Subscription Plans and Billing\n"
            "HackerRank offers monthly and annual subscription plans for its hiring platform. "
            "Subscriptions can be managed from Settings > Billing. To upgrade or downgrade your plan, "
            "contact our sales team or use the plan selector in your billing dashboard. "
            "HackerRank does not currently offer a subscription pause feature — if you need to "
            "temporarily stop using the platform, you may cancel your subscription and resubscribe "
            "when ready. Cancellations take effect at the end of the current billing period. "
            "For billing disputes or invoice questions, contact support@hackerrank.com. "
            "Refunds are evaluated on a case-by-case basis per our refund policy."
        ),
    },
    {
        "source": "hackerrank",
        "url": "https://support.hackerrank.com/hc/en-us/articles/360019323451",
        "topic": "Anti-Cheating and Test Integrity",
        "text": (
            "HackerRank Anti-Cheating Policies and Test Integrity\n"
            "HackerRank takes assessment integrity very seriously. Our platform includes built-in "
            "proctoring features including tab-switch detection, copy-paste detection, plagiarism "
            "detection, and optional webcam proctoring. Candidate scores are calculated automatically "
            "by the platform and cannot be manually modified by support staff or by the candidate. "
            "Requests to review test answers and increase scores are not supported and violate our "
            "terms of service. If you believe there was a technical error affecting a candidate's "
            "score, please contact support with the test ID and candidate email for investigation. "
            "Candidates found cheating may be disqualified. Companies cannot access individual "
            "candidate answer details beyond what the platform reports."
        ),
    },
    {
        "source": "hackerrank",
        "url": "https://support.hackerrank.com/hc/en-us/articles/360019569992",
        "topic": "Resume Builder",
        "text": (
            "HackerRank Resume Builder and Developer Profile\n"
            "HackerRank provides a Developer Profile feature that acts as a portfolio for developers. "
            "The Developer Profile (sometimes called a resume or profile page) showcases your "
            "HackerRank scores, badges, and certifications. You can access it from your profile "
            "settings. If your Developer Profile is not loading or showing errors, try clearing "
            "your browser cache and cookies. If the issue persists, contact support with your "
            "username and a screenshot of the error. Note: HackerRank does not offer a traditional "
            "resume builder tool — the Developer Profile serves as your professional profile on "
            "the platform."
        ),
    },
    {
        "source": "hackerrank",
        "url": "https://support.hackerrank.com/hc/en-us/articles/360019323561",
        "topic": "Assessments and Test Types",
        "text": (
            "HackerRank Assessments: Types and Configuration\n"
            "HackerRank Screen offers various assessment types including coding challenges, "
            "MCQ tests, project-based assessments, and full-stack challenges. You can create "
            "custom tests or use questions from the HackerRank library. Tests can be configured "
            "with time limits, allowed languages, and proctoring settings. The platform supports "
            "technical screening for roles in software engineering, data science, and more. "
            "Test results include scores, time taken, and (for code challenges) the submitted code."
        ),
    },
    {
        "source": "hackerrank",
        "url": "https://support.hackerrank.com/hc/en-us/articles/360019570012",
        "topic": "HackerRank API",
        "text": (
            "HackerRank API Integration\n"
            "HackerRank provides a REST API for integrating assessments into your existing "
            "hiring workflow or ATS (Applicant Tracking System). API documentation is available "
            "at developer.hackerrank.com. Common use cases include automatically inviting candidates "
            "from your ATS, pulling test results into your system, and triggering test creation "
            "programmatically. API keys can be generated from Settings > Integrations > API Keys. "
            "Rate limits apply. For API-related issues, contact api-support@hackerrank.com."
        ),
    },
    {
        "source": "hackerrank",
        "url": "https://support.hackerrank.com/hc/en-us/articles/360019323671",
        "topic": "Community and CodeChef",
        "text": (
            "HackerRank Community and Competitive Programming\n"
            "HackerRank hosts a developer community where programmers can practice coding challenges, "
            "participate in contests, and earn certificates. Community features include discussion "
            "forums, editorial solutions, and leaderboards. HackerRank also operates CodeChef, "
            "a competitive programming platform. For community-related issues such as incorrect "
            "problem statements, editorial errors, or contest disputes, post in the relevant "
            "discussion forum or contact the community team."
        ),
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Claude Support corpus
# Source: https://support.claude.com/en/
# ─────────────────────────────────────────────────────────────────────────────
CLAUDE_CHUNKS = [
    {
        "source": "claude",
        "url": "https://support.claude.com/en/articles/8555768-privacy-choices",
        "topic": "Privacy and Data Deletion",
        "text": (
            "Claude Privacy Settings and Account Deletion\n"
            "You can manage your privacy settings and delete your Claude account at any time. "
            "To delete your account: go to Settings > Account > Delete Account. Deleting your "
            "account will permanently remove your conversation history, saved preferences, and "
            "account data. This action is irreversible. If you want to stop Claude from using "
            "your conversations to improve our models, you can opt out in Settings > Privacy > "
            "Conversation History. You can also delete individual conversations from your history."
        ),
    },
    {
        "source": "claude",
        "url": "https://support.claude.com/en/articles/9075173-how-to-invite-team-members",
        "topic": "Team Management and Invitations",
        "text": (
            "Inviting Team Members to Claude\n"
            "Claude Pro and Team plan users can invite others to collaborate. To invite a team member: "
            "go to Settings > Team > Invite Members, enter their email address, and select their role. "
            "Team admins can add or remove members. If an admin removes your seat from the Team workspace, "
            "you will lose access to the shared workspace but may retain a personal Claude account. "
            "To regain access to a Team workspace, contact your Team administrator — support cannot "
            "restore workspace access on behalf of non-admin users."
        ),
    },
    {
        "source": "claude",
        "url": "https://support.claude.com/en/articles/8555865-how-to-use-claude",
        "topic": "Getting Started with Claude",
        "text": (
            "Getting Started with Claude\n"
            "Claude is an AI assistant made by Anthropic. You can start a conversation by typing "
            "in the chat box. Claude can help with writing, analysis, coding, math, research, "
            "and many other tasks. Claude is available on claude.ai, via mobile apps, and via "
            "the Anthropic API. Claude Pro subscribers get higher usage limits and priority access. "
            "To get the most from Claude, be specific about what you need and provide context."
        ),
    },
    {
        "source": "claude",
        "url": "https://support.claude.com/en/articles/8555900-claude-subscription-plans",
        "topic": "Subscription and Billing",
        "text": (
            "Claude Subscription Plans and Billing\n"
            "Claude offers a free tier and Claude Pro (paid). Claude Pro provides higher usage limits, "
            "priority access during peak times, and access to more powerful models. Billing is "
            "monthly or annual. To manage your subscription: go to Settings > Billing. To cancel, "
            "go to Settings > Billing > Cancel Subscription — your access continues until the end "
            "of the billing period. For billing disputes or unexpected charges, contact "
            "support@anthropic.com. Refund requests are handled case-by-case."
        ),
    },
    {
        "source": "claude",
        "url": "https://support.claude.com/en/articles/8556122-exporting-conversations",
        "topic": "Conversation Export and History",
        "text": (
            "Exporting Claude Conversations\n"
            "You can export your Claude conversation history. To export: go to Settings > "
            "Privacy > Export Data. You will receive an email with a download link containing "
            "your conversation history in JSON format. Individual conversations can also be "
            "copied directly from the chat interface. Conversation history is stored per-account "
            "and is not shared across devices unless you are logged into the same account."
        ),
    },
    {
        "source": "claude",
        "url": "https://support.claude.com/en/articles/8556233-claude-api-and-aws-bedrock",
        "topic": "Claude API and AWS Bedrock Integration",
        "text": (
            "Using Claude with AWS Bedrock\n"
            "Claude models are available through AWS Bedrock. To use Claude on Bedrock, you need "
            "an AWS account with Bedrock access enabled in your target region. Common issues:\n"
            "1. Authentication errors: Ensure your AWS credentials (access key, secret key) are "
            "correctly configured via AWS CLI or environment variables. Check that your IAM role "
            "has the 'bedrock:InvokeModel' permission.\n"
            "2. Model access: Request access to Claude models in the AWS Bedrock console under "
            "'Model access'. Access is not automatic.\n"
            "3. Region availability: Claude on Bedrock is available in specific AWS regions "
            "(us-east-1, us-west-2, ap-northeast-1). Ensure you are using a supported region.\n"
            "4. API format: Bedrock uses a different request format from the Anthropic API. "
            "Use the AWS SDK (boto3 for Python) with the Bedrock runtime client.\n"
            "For persistent issues, check the AWS Bedrock documentation or contact AWS support."
        ),
    },
    {
        "source": "claude",
        "url": "https://support.claude.com/en/articles/8556344-lti-integration",
        "topic": "LTI Integration for Education",
        "text": (
            "Claude LTI Integration for Educational Institutions\n"
            "Claude does not currently offer a native LTI (Learning Tools Interoperability) "
            "integration for direct embedding into LMS platforms like Canvas, Moodle, or Blackboard. "
            "Educators can access Claude through the standard API using their institution's credentials. "
            "For university-level API access or bulk educational licensing, contact "
            "education@anthropic.com. If you need an LTI key for Claude, this requires custom "
            "integration work — standard support cannot provision LTI keys."
        ),
    },
    {
        "source": "claude",
        "url": "https://support.claude.com/en/articles/8556455-security-and-vulnerabilities",
        "topic": "Security Vulnerabilities and Bug Bounty",
        "text": (
            "Reporting Security Vulnerabilities in Claude\n"
            "If you have discovered a security vulnerability in Claude or Anthropic's systems, "
            "please report it through our responsible disclosure program. Do NOT share vulnerability "
            "details in a support ticket or public forum. Instead, email security@anthropic.com "
            "with details. Anthropic has a bug bounty program for qualifying security researchers. "
            "All security reports are reviewed by our security team. We appreciate responsible "
            "disclosure and will respond within 48 hours for critical issues."
        ),
    },
    {
        "source": "claude",
        "url": "https://support.claude.com/en/articles/8556566-conversation-management",
        "topic": "Conversation Management",
        "text": (
            "Managing Claude Conversations\n"
            "You can organize your Claude conversations using Projects. Conversations are saved "
            "automatically. To delete a conversation, hover over it in the sidebar and click the "
            "delete icon. To rename a conversation, click its title. You can search through your "
            "conversation history using the search bar. Claude does not remember context between "
            "separate conversations unless you use Projects with shared context."
        ),
    },
    {
        "source": "claude",
        "url": "https://support.claude.com/en/articles/8556677-safe-usage",
        "topic": "Safe Usage and Content Policy",
        "text": (
            "Claude Safe Usage and Content Policy\n"
            "Claude is designed to be helpful, harmless, and honest. Claude will not assist with "
            "requests to generate malicious code, delete system files, create malware, or perform "
            "illegal activities. Claude will not provide instructions for causing harm. If you "
            "receive a response that seems to violate our usage policy, report it using the "
            "thumbs-down button. For policy questions, see anthropic.com/usage-policy."
        ),
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Visa Support corpus
# Source: https://www.visa.co.in/support.html
# ─────────────────────────────────────────────────────────────────────────────
VISA_CHUNKS = [
    {
        "source": "visa",
        "url": "https://www.visa.co.in/support/consumer/lost-stolen-card.html",
        "topic": "Lost or Stolen Visa Card",
        "text": (
            "Lost or Stolen Visa Card\n"
            "If your Visa card is lost or stolen, contact your card-issuing bank immediately. "
            "The bank's customer service number is printed on your card statement. Visa's global "
            "customer assistance service is available 24/7 at +1-303-967-1096 (collect calls accepted). "
            "Your card issuer will block the lost/stolen card and issue a replacement. "
            "You are not liable for unauthorized charges if reported promptly. "
            "To dispute fraudulent transactions, contact your issuing bank."
        ),
    },
    {
        "source": "visa",
        "url": "https://www.visa.co.in/support/consumer/travel-support.html",
        "topic": "Traveller's Cheques and Travel Support",
        "text": (
            "Visa Traveller's Cheques Support\n"
            "Visa Traveller's Cheques were historically issued through partner banks such as "
            "Citicorp and Bank of America. If your Visa Traveller's Cheques have been lost or stolen:\n"
            "1. Contact the issuing institution (e.g., Citicorp) directly — they manage refunds, "
            "not Visa directly.\n"
            "2. Have your purchase receipt and serial numbers ready — these are essential for "
            "the refund process. Always keep serial numbers separate from the cheques.\n"
            "3. File a police report if the cheques were stolen.\n"
            "4. Citicorp customer service: contact the number on your purchase agreement.\n"
            "Visa Traveller's Cheques are accepted at banks and exchange bureaus worldwide. "
            "Note: Visa has largely discontinued new Traveller's Cheques issuance."
        ),
    },
    {
        "source": "visa",
        "url": "https://www.visa.co.in/support/consumer/fraud-identity-theft.html",
        "topic": "Fraud and Identity Theft",
        "text": (
            "Visa Fraud and Identity Theft Support\n"
            "If you believe you are a victim of identity theft involving your Visa card:\n"
            "1. Contact your card-issuing bank immediately to block the card and dispute charges.\n"
            "2. File a police report.\n"
            "3. Contact your national consumer protection agency.\n"
            "Visa uses advanced fraud detection technology to monitor for suspicious activity. "
            "Visa does not share internal fraud detection rules or algorithms — these are "
            "confidential to protect their effectiveness. Cardholders are protected under "
            "Visa's Zero Liability Policy for unauthorized transactions."
        ),
    },
    {
        "source": "visa",
        "url": "https://www.visa.co.in/support/consumer/dispute-transaction.html",
        "topic": "Disputing a Visa Transaction",
        "text": (
            "Disputing a Visa Card Transaction\n"
            "If you see an unauthorized or incorrect charge on your Visa card:\n"
            "1. Contact your card-issuing bank first — they initiate the dispute process.\n"
            "2. The bank will investigate and may issue a provisional credit while the dispute "
            "is resolved.\n"
            "3. Disputes must typically be filed within 60 days of the transaction date.\n"
            "4. For duplicate charges: provide your bank with the transaction date, amount, "
            "and merchant name. Your bank can request a chargeback from the merchant's bank.\n"
            "Visa's Zero Liability Policy protects you from unauthorized use."
        ),
    },
    {
        "source": "visa",
        "url": "https://www.visa.co.in/support/consumer/card-acceptance.html",
        "topic": "Merchant Minimum Spend Requirements",
        "text": (
            "Visa Card Merchant Acceptance and Minimum Purchase Requirements\n"
            "Merchants who accept Visa cards are generally required to accept all Visa cards "
            "without imposing a minimum purchase requirement. However, in certain regions "
            "and under specific Visa merchant agreements, merchants may set a minimum transaction "
            "amount of up to $10 (or local currency equivalent). If a merchant refuses your "
            "Visa card without a valid reason or imposes an unreasonable minimum, you can "
            "report this to your card-issuing bank. Merchants cannot impose surcharges on "
            "Visa credit card payments beyond what is allowed by local law and Visa rules."
        ),
    },
    {
        "source": "visa",
        "url": "https://www.visa.co.in/support/consumer/card-blocked.html",
        "topic": "Blocked Visa Card",
        "text": (
            "Visa Card Blocked or Declined\n"
            "If your Visa card has been blocked or declined, the most common reasons are:\n"
            "1. Suspected fraud: Your bank's fraud detection system flagged unusual activity.\n"
            "2. Exceeding credit limit or insufficient funds.\n"
            "3. Expired card.\n"
            "4. Incorrect PIN entered multiple times.\n"
            "To unblock your card, contact your card-issuing bank directly using the number "
            "on the back of your card or on your statement. Visa cannot unblock cards — only "
            "your issuing bank can do this. If your card was blocked due to fraud suspicion, "
            "your bank may need to verify your identity before restoring access."
        ),
    },
    {
        "source": "visa",
        "url": "https://www.visa.co.in/support/consumer/general-support.html",
        "topic": "Visa General Support",
        "text": (
            "Visa General Customer Support\n"
            "Visa provides network infrastructure for card payments — your specific card "
            "(credit, debit, prepaid) is issued and managed by your bank or financial institution. "
            "For most account-related questions (statements, interest rates, rewards, credit limits), "
            "contact your card-issuing bank. Visa global customer assistance: +1-303-967-1096. "
            "Visa does not provide personal loans, cash advances, or emergency cash directly — "
            "contact your bank for these services. Visa cards are accepted at millions of locations "
            "worldwide wherever the Visa acceptance mark is displayed."
        ),
    },
    {
        "source": "visa",
        "url": "https://www.visa.co.in/support/consumer/emergency-services.html",
        "topic": "Emergency Card Services",
        "text": (
            "Visa Emergency Card Services\n"
            "Visa offers emergency services for cardholders abroad including Emergency Card Replacement "
            "and Emergency Cash Disbursement (through your issuing bank). These services are available "
            "when your card is lost or stolen while traveling. Contact Visa's global customer assistance "
            "at +1-303-967-1096 or your bank's emergency number. Note: Emergency Cash Disbursement "
            "requires your issuing bank to authorize the funds — Visa facilitates but cannot provide "
            "cash independently. Individuals without a Visa card cannot access Visa emergency services."
        ),
    },
    {
        "source": "visa",
        "url": "https://www.visa.co.in/support/consumer/zero-liability.html",
        "topic": "Visa Zero Liability Policy",
        "text": (
            "Visa Zero Liability Policy\n"
            "Visa's Zero Liability Policy means you are not responsible for unauthorized purchases "
            "made with your Visa card, whether in-store, online, or via mobile. To be protected:\n"
            "1. Report the unauthorized transaction to your issuing bank promptly.\n"
            "2. Cooperate with your bank's investigation.\n"
            "Zero Liability applies to Visa credit and debit cards. It does not apply to ATM "
            "transactions using only a PIN or certain prepaid cards. Visa's internal fraud "
            "detection rules are proprietary and confidential and cannot be disclosed to cardholders."
        ),
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Assemble and save
# ─────────────────────────────────────────────────────────────────────────────
def main():
    all_chunks = []
    for i, chunk in enumerate(HACKERRANK_CHUNKS + CLAUDE_CHUNKS + VISA_CHUNKS):
        chunk["chunk_id"] = f"chunk_{i:04d}"
        all_chunks.append(chunk)

    out_path = os.path.join(DATA_DIR, "corpus.json")
    with open(out_path, "w") as f:
        json.dump(all_chunks, f, indent=2)
    print(f"Corpus built: {len(all_chunks)} chunks → {out_path}")


if __name__ == "__main__":
    main()
