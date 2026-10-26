# URL input routing correction — 2026-10-26

Two reported inputs exposed routing errors before supervised inference:

- A space or newline before an explicit URL caused the punctuation alternative
  in `<url>|[\W_]+` to consume the opening `<` of a URL placeholder. The remaining
  `URL` was mistaken for message text, activating the SMS head. The reported
  Belgium profile URL consequently displayed SMS score 89 instead of URL score 70.
- The training-era extractor's fixed suffix list matched `sunwin.org` inside
  `sunwin.org.vc`. The remaining `.vc` activated SMS, displaying SMS score 6 and
  URL score 65 for the wrong hostname.

The hybrid input adapter now removes entire URL placeholders before testing for
message text and extracts complete bare hostnames, including unlisted suffixes.
It reuses the existing URL canonicalizer. Training preprocessing and its bound
checksums remain frozen, as do fitted weights, labels and detection thresholds.
Actual prose still activates SMS, with independent URL review when appropriate.

With the active `hybrid-isolated-20261026-icann` bundle, the reported profile URL
now consistently displays URL score 70 with or without leading whitespace.
`sunwin.org.vc` is evaluated as `http://sunwin.org.vc`, consistently scoring 88
through either API and either input field. Bare domains retain the existing
default HTTP scheme. These are uncalibrated model outputs, not live website
verification or measured fraud probabilities.

Verification: 84 Python tests, 18 assessment tests, 13 API integration tests,
ESLint and the production build passed. Four isolated Chrome scenarios checked
leading spaces, line breaks, the complete domain and a 375px mobile viewport;
all displayed the URL branch without browser errors or horizontal overflow.
Regression cases also cover multiple URLs, punctuation wrappers, genuine mixed
messages, email addresses and decimal numbers.

## Incomplete URL follow-up

The standalone input `https://` had no extractable URL, so its remaining letters
activated the SMS estimator and produced 100 points. The hybrid adapter now
validates standalone HTTP/HTTPS URL-like inputs and explicit URL fields before
loading either model. Missing hosts, incomplete scheme separators and `www.`
return `INVALID_URL` with no score. Both web endpoints translate this into HTTP
400 and a Vietnamese or English instruction to enter a complete hostname.
Messages that mention an incomplete URL within actual prose remain SMS inputs.

The page clears its previous result and case ID when analysis fails, so an old
score is not displayed alongside the validation error. Python regression tests
cover the incomplete forms in both input fields; API tests check the 400
response and absence of score fields. Isolated Chrome checks verify Vietnamese
desktop and English mobile errors after a successful analysis, including removal
of the previous result. The fitted model and thresholds remain unchanged.
