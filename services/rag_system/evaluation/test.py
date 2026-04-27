from ragas import evaluate
from ragas.metrics import (
    Faithfulness,
    ResponseRelevancy,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
)


from ragas.llms import llm_factory
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_huggingface import HuggingFaceEmbeddings
from openai import OpenAI
from datasets import Dataset

client = OpenAI(
    api_key="ff9d204547ac4da9a3b2c8c39eef4ae7.mM-OSzKf_wkFI55Q36YjVrRR",
    base_url="https://ollama.com/v1",
)

evaluator_llm = llm_factory(
    model="gpt-oss:120b",
    provider="openai",
    client=client,
)

evaluator_embeddings = LangchainEmbeddingsWrapper(
    HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
)

data = {
    "user_input": [
        "Ban giám hiệu nhà trường gồm những ai?",
        "Quy trình xin nghỉ phép của giáo viên như thế nào?",
        "Thời gian làm việc của văn phòng nhà trường?",
        "Học sinh vi phạm nội quy sẽ bị xử lý như thế nào?",
        "Nhà trường có những câu lạc bộ ngoại khóa nào?",
    ],
    "response": [
        "Ban giám hiệu gồm Hiệu trưởng và 03 Phó Hiệu trưởng phụ trách chuyên môn, cơ sở vật chất và công tác học sinh.",
        "Giáo viên điền mẫu đơn, nộp cho tổ trưởng chuyên môn trước 3 ngày, chờ Ban Giám hiệu phê duyệt.",
        "Văn phòng làm việc thứ Hai đến thứ Sáu, sáng 7h30-11h30, chiều 13h30-17h00.",
        "Tùy mức độ vi phạm: nhắc nhở, cảnh cáo trước lớp, thông báo phụ huynh hoặc đình chỉ học tập.",
        "Nhà trường có 5 câu lạc bộ: Tiếng Anh, Tin học, Thể thao, Văn nghệ và Kỹ năng sống.",
    ],
    "retrieved_contexts": [
        [
            "Ban Giám hiệu nhà trường bao gồm Hiệu trưởng và 03 Phó Hiệu trưởng.",
            "Các Phó Hiệu trưởng phụ trách: chuyên môn, cơ sở vật chất và công tác học sinh sinh viên.",
        ],
        [
            "Giáo viên có nhu cầu nghỉ phép cần điền đầy đủ mẫu đơn theo quy định.",
            "Đơn phải nộp cho tổ trưởng chuyên môn trước ít nhất 03 ngày làm việc để trình Ban Giám hiệu phê duyệt.",
        ],
        [
            "Giờ làm việc văn phòng: Sáng 7h30-11h30, Chiều 13h30-17h00.",
            "Văn phòng làm việc từ thứ Hai đến thứ Sáu, nghỉ thứ Bảy và Chủ nhật.",
        ],
        [
            "Hình thức kỷ luật học sinh: nhắc nhở, cảnh cáo trước lớp, cảnh cáo toàn trường, thông báo gia đình, đình chỉ học tập.",
            "Mức độ xử lý tùy thuộc tính chất và mức độ nghiêm trọng của vi phạm.",
        ],
        [
            "Các câu lạc bộ tại trường: CLB Tiếng Anh, CLB Tin học, CLB Thể thao.",
            "CLB Văn nghệ và CLB Kỹ năng sống sinh hoạt định kỳ chiều thứ Sáu hàng tuần.",
        ],
    ],
    "reference": [
        "Ban giám hiệu gồm Hiệu trưởng và 03 Phó Hiệu trưởng phụ trách chuyên môn, cơ sở vật chất và công tác học sinh.",
        "Quy trình: điền mẫu đơn → nộp tổ trưởng trước 3 ngày → Ban Giám hiệu phê duyệt.",
        "Văn phòng làm việc thứ Hai đến thứ Sáu, sáng 7h30-11h30, chiều 13h30-17h00.",
        "Học sinh vi phạm bị xử lý theo các mức: nhắc nhở, cảnh cáo, thông báo phụ huynh, đình chỉ học tập.",
        "Nhà trường có 5 câu lạc bộ: Tiếng Anh, Tin học, Thể thao, Văn nghệ, Kỹ năng sống.",
    ],
}

dataset = Dataset.from_dict(data)

results = evaluate(
    dataset=dataset,
    metrics=[
        Faithfulness(),
        ResponseRelevancy(),
        LLMContextPrecisionWithReference(),
        LLMContextRecall(),
    ],
    llm=evaluator_llm,
    embeddings=evaluator_embeddings,
)

print(results)

results.to_pandas().to_json(
    "data/evaluation/results.json",
    orient="records",
    force_ascii=False,
    indent=2,
)