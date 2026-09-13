def run_agent(document_text):
    """
    Simple agentic screening workflow.
    """

    text = document_text.lower()

    checks = []

    # Step 1: Observe
    if not document_text.strip():
        return {
            "status": "REJECTED",
            "risk_score": 100,
            "reason": "No readable document text found."
        }

    # Step 2: Decide what checks are needed
    checks.append("OCR text availability check")

    # Step 3: Act
    suspicious_words = [
        "fake",
        "sample",
        "invalid",
        "dummy",
        "test document"
    ]

    suspicious_found = [
        word for word in suspicious_words
        if word in text
    ]

    if suspicious_found:
        checks.append("Suspicious keyword detection")
        risk_score = 80
        status = "HIGH RISK"
    else:
        checks.append("Basic identity text consistency check")
        risk_score = 20
        status = "LOW RISK"

    # Step 4: Evaluate
    if risk_score >= 70:
        decision = "Manual verification required"
    else:
        decision = "Document passed initial screening"

    # Step 5: Return result
    return {
        "status": status,
        "risk_score": risk_score,
        "checks_performed": checks,
        "decision": decision
    }
