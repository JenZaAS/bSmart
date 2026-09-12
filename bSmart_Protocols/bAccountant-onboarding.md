# bAccountant onboarding protocol

## Interaction contract

- Ask exactly one question per turn.
- Use options whenever a bounded choice is possible.
- Put the recommended option first and mark it as recommended in the UI.
- Include `Other / specify` and `Later` where appropriate.
- Do not infer missing legal, tax, ownership, or responsibility information.
- Save each answer and its source/status; corrections supersede earlier answers without deleting history.
- Do not connect to Tripletex or enable a write-capable mode until the relevant approval and credential questions are complete.

## Stage 1 — Initial context

Ask in this order, adapting only when an answer makes a question irrelevant:

1. Country whose laws govern the business. **Recommendation:** select the actual jurisdiction of the legal entity.
2. Legal entity type and organisation/company number. **Recommendation:** provide the exact registered entity.
3. Business activity and main products/services. **Recommendation:** describe actual invoiced activities, not a broad industry label.
4. Countries of customers and suppliers. **Recommendation:** include domestic, EU/EEA, and non-EU/non-EEA activity separately.
5. Accounting bureau involvement. **Recommendation:** identify the bureau and what it is responsible for.
6. Division of labour. **Recommendation:** name who prepares, reviews, approves, posts, pays, reconciles, and submits reports.
7. Human escalation contact. **Recommendation:** one named person with authority to decide uncertain accounting questions.
8. Tripletex company/tenant and MCP connection. **Recommendation:** verify identity and use read-only access first.
9. Available Tripletex/MCP operations. **Recommendation:** start with the minimum required permissions.
10. Initial mode settings. **Recommendation:** read-only on; learning on if the user wants comparison data; salary and bookkeeping off.
11. Approval policy. **Recommendation:** explicit approval per item until the workflow is proven safe.
12. Audit and daily-report recipients. **Recommendation:** send reports to the responsible human and retain an immutable local record.
13. Data and retention constraints. **Recommendation:** store no secrets in bSmart content and minimize copied personal data.

## Stage 2 — Research and confirmation

After Stage 1, produce a short, cited research plan and ask one confirmation question at a time for:

- applicable accounting law and official authorities;
- bookkeeping and voucher requirements;
- VAT registration, rates, deductions, periods, domestic rules, imports/exports, and reverse charge;
- payroll and employer obligations, if salary mode is requested;
- procedures already covered by Tripletex;
- company-specific rules that require human approval.

Research findings are advisory until a responsible human confirms the applicable policy. Unresolved or conflicting rules remain exceptions and block automated action.

## Completion gate

Do not mark onboarding complete until:

- business context and responsibility boundaries are recorded;
- Tripletex identity and MCP permissions are verified;
- read-only behavior and audit logging are tested;
- country/VAT research has cited sources or is explicitly pending;
- mode settings and approval policy are explicitly confirmed.
