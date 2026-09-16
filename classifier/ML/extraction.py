import json
import os
from pathlib import Path
"""
Using the Ollama API from the huggingface, for extracting the PDF texts.
- pip install ollama --break-system-packages

Using the KoBART, HuggingFace Transformers for text generation and processing.
- pip install transformers --break-system-packages

pip install transformers torch

curl -fsSL https://ollama.com/install.sh | sh
ollama --version
ollama serve
ollama pull qwen2.5:7b
"""
import ollama

from transformers import PreTrainedTokenizerFast, BartForConditionalGeneration
"""  The model takes your system prompt + document text, converts it
     into tokens, and trained network, running on your own hardware instead of a company's servers.
"""
# for the ollama extraction model. 
EXTRACTION_MODEL = os.environ.get("EXTRACTION_MODEL", "qwen2.5:1.5b")

# Structure of the extracted data from the PDF using the Ollama.
JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "valid_until": {"type": "string"},
        "document_type": {"type": "string"},
        "stamp_present": {"type": "boolean"},
        "confidence": {"type": "number"},
    },
    "required": ["name", "valid_until", "document_type", "stamp_present", "confidence"],
}

#Giving the system prompt. To extract the PDF file information accurately.
EXTRACTION_SYSTEM_PROMPT = """당신은 예비군 관련 서류(진단서, 재직증명서 등)에서 정보를 추출하는 어시스턴트입니다.
주어진 문서 텍스트에서 다음 필드를 정확히 추출하여 JSON으로만 응답하세요:
- name: 서류에 명시된 이름
- valid_until: 서류의 유효기간 종료일 (YYYY-MM-DD 형식, 확인 불가능하면 빈 문자열)
- document_type: 서류 종류 (예: 진단서, 재직증명서, 출입국사실증명서 등)
- stamp_present: 도장/직인이 있는 것으로 보이면 true, 아니면 false
- confidence: 추출 결과에 대한 0~1 사이의 신뢰도 in float
다른 설명 없이 JSON_SCHEMA 형식으로 반환하세요."""

def extract_pdf(doc_text: str) -> dict:
    try:
        response = ollama.chat(
            model=EXTRACTION_MODEL,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": doc_text}
            ],
            format=JSON_SCHEMA,
            options={"temperature": 0.1},
        )
    except ConnectionError as exc:
        host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
        raise RuntimeError(
            f"Ollama 서버에 연결할 수 없습니다 ({host}). "
            f"Ollama를 실행하고 `ollama pull {EXTRACTION_MODEL}`을 먼저 실행하세요."
        ) from exc

    # Getting the output of the extraction text.
    output = response["message"]["content"]

    # checking for the json output.
    try:
        res = json.loads(output)
    except json.JSONDecodeError:
        print("Failed to decode JSON from output:", output)
        res = {
            "name": "",
            "valid_until": "",
            "document_type": "",
            "stamp_present": False,
            "confidence": 0.0,
            "_raw_error": output,
        }

    return res

# Summarize the text from the json fromat using the KoBART model.
SUMMARIZATION_MODEL = "gogamza/kobart-summarization"
_summarization_tokenizer = None
_summarization_model = None
SAMPLE_DATA_PATH = Path(__file__).with_name("sample_data.json")

def load_summarization_model():
    global _summarization_tokenizer, _summarization_model
    if _summarization_tokenizer is None or _summarization_model is None:
        # Load the tokenizer and model for summarization if they haven't been loaded yet.
        _summarization_tokenizer = PreTrainedTokenizerFast.from_pretrained(SUMMARIZATION_MODEL)
        _summarization_model = BartForConditionalGeneration.from_pretrained(SUMMARIZATION_MODEL)

    return _summarization_tokenizer, _summarization_model

def summarize_text(text: str, MAX_LEN: int) -> str:
    # Load the summarization model and tokenizer if they haven't been loaded yet.
    token, model = load_summarization_model()

    inputs = token(text, return_tensors="pt", max_length=512, truncation=True)
    # Generate the summary using the model.
    res_id = model.generate(
        inputs["input_ids"],
        max_length=MAX_LEN,
        num_beams = 4,
        early_stopping = True
    )

    for i, res in enumerate(res_id):
        summary = token.decode(res, skip_special_tokens=True)
        print(f"Summary {i}: {summary}")

    return summary

"""--------------------------------------------------------------------------------------------"""
def load_sample_data() -> dict:
    return json.loads(SAMPLE_DATA_PATH.read_text(encoding="utf-8"))


def run_samples(run_all: bool = False) -> None:
    data = load_sample_data()
    documents = data["documents"] if run_all else data["documents"][:1]
    reasons = data["reasons"] if run_all else data["reasons"][:1]

    print(f"=== 문서 추출 ({len(documents)}건) ===")
    for document in documents:
        fields = extract_pdf(document["text"])
        print(f"\n[{document['id']}]")
        print(json.dumps(fields, ensure_ascii=False, indent=2))

    print(f"\n=== 개인사유서 요약 ({len(reasons)}건) ===")
    for reason in reasons:
        summary = summarize_text(reason["text"], MAX_LEN=100)
        print(f"\n[{reason['id']}] {reason['label']}")
        print(summary)


# TESTING PART.
if __name__ == "__main__":
    run_samples(run_all="--all" in os.sys.argv)