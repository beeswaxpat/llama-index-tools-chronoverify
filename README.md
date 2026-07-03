# LlamaIndex Tools Integration: ChronoVerify

Verify when a photo was taken and its provenance from a LlamaIndex agent.

[ChronoVerify](https://chronoverify.com) checks an image for C2PA Content Credentials, EXIF capture metadata, and pixel-level consistency, then returns a structured verdict (`provenance_confirmed`, `consistent`, `inconclusive`, `metadata_anomaly`, or `manipulation_indicated`) with a confidence score from 0 to 100, the capture time, capture device, and capture location when available, and file hashes.

ChronoVerify validates provenance. It is not a deepfake or AI-generation detector. Treat results as investigative triage, not proof.

## Installation

```bash
pip install llama-index-tools-chronoverify
```

## API key

The tool works without an API key on a free, rate limited keyless tier. For metered use, get a free API key:

```bash
curl -X POST https://chronoverify.com/v1/keys/free -d "email=you@example.com"
```

Set it as an environment variable:

```bash
export CHRONOVERIFY_API_KEY=cv_live_...
```

## Usage

```python
from llama_index.tools.chronoverify import ChronoVerifyToolSpec
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI

tool_spec = ChronoVerifyToolSpec()
# or with a key: ChronoVerifyToolSpec(api_key="cv_live_...")

agent = FunctionAgent(
    tools=tool_spec.to_tool_list(),
    llm=OpenAI(model="gpt-4.1"),
)

print(
    await agent.run(
        "When was the photo at https://example.com/photo.jpg taken, "
        "and does it carry valid provenance?"
    )
)
```

Direct call without an agent:

```python
result = tool_spec.verify_image_provenance(url="https://example.com/photo.jpg")
# or from a local file:
result = tool_spec.verify_image_provenance(file_path="/path/to/photo.jpg")

print(result["verdict"], result["confidence"])
```

### Available functions

- **verify_image_provenance**: Verify when a photo was taken and its provenance. Accepts exactly one of `url` (a public image URL) or `file_path` (a local image file to upload). Returns the API response as a dict with the verdict, confidence, capture details, C2PA validation results, and integrity hashes.

## API reference

- Machine-readable onboarding: https://chronoverify.com/v1/onboarding
- Response schema: https://chronoverify.com/v1/verify.schema.json
