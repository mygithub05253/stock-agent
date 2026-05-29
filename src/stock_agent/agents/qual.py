import os
import json
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI

from stock_agent.schemas.analysis import AgentState, QualResult
from stock_agent.tools.rag_tool import get_disclosure_context

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# 유저님의 GLM 환경 변수 지원 및 OpenAI 호환 클라이언트 바인딩
client = OpenAI(
    api_key=os.getenv("GLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "mock-key",
    base_url=os.getenv("GLM_BASE_URL") or os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
)

def run_qual(state: AgentState) -> AgentState:
    """
    [Qual Agent] 기준일 이전 1주일간의 공시 원문을 수집하고 LLM을 통해 정성 센티멘트를 분석합니다.
    """
    if state.curator is None:
        raise ValueError("Curator result is required before qual analysis")

    corp_code = state.curator.corp_code
    
    # 윈도우 기간 설정 (5월 21일 기준 15일 ~ 21일 타깃팅)
    as_of_date_str = getattr(state, "as_of_date", "2026-05-21")
    as_of_date = datetime.strptime(as_of_date_str, "%Y-%m-%d")
    start_date = (as_of_date - timedelta(days=6)).strftime("%Y-%m-%d")
    end_date = as_of_date_str

    # 1. DB에서 공시 원문 로드
    conn = psycopg2.connect(DATABASE_URL)
    try:
        disclosure_docs = get_disclosure_context(conn, corp_code, start_date, end_date)
    finally:
        conn.close()

    # 텍스트 조립 및 컨텍스트 길이 방어 (상위 3000자 슬라이싱)
    context_str = ""
    if disclosure_docs:
        for doc in disclosure_docs:
            context_str += f"\n\n[공시명: {doc['report_nm']} / 공시일: {doc['rcept_dt']}]\n"
            context_str += doc['content'][:3000]
    else:
        context_str = "해당 기간 내에 발행된 공시 보고서 원문이 없습니다."

    # 2. 시스템 프롬프트 로드
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.abspath(os.path.join(current_file_dir, "..", "prompts", "qual", "system.md"))
    
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        system_prompt = "주어진 공시 데이터를 바탕으로 score, sentiment, event_types, evidence, risks가 포함된 JSON을 반환하라."

    # 3. LLM 호출
    user_message = f"분석 대상 기업의 공시 데이터셋:\n{context_str}"
    model_name = os.getenv("GLM_MODEL") or os.getenv("LLM_MODEL") or "glm-4.5-flash"
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        # GLM/OpenAI 펜스 가드레일 제거 후 파싱
        raw_content = response.choices[0].message.content
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        parsed_result = json.loads(raw_content)
    except Exception as e:
        print(f"⚠️ Qual LLM 장애로 인한 폴백 작동: {e}")
        parsed_result = {
            "score": 50,
            "sentiment": "neutral",
            "event_types": ["시스템폴백"],
            "evidence": ["해당 기간 내 특이 공시 이력 없음"],
            "risks": ["해당 기간 내 특이 공시 이력 없음"]
        }

    # 안전 가드: 에러 방지를 위해 빈 리스트가 넘어오면 강제로 기본 문장 채우기
    if not parsed_result.get("evidence"): parsed_result["evidence"] = ["해당 기간 내 특이 공시 이력 없음"]
    if not parsed_result.get("risks"): parsed_result["risks"] = ["해당 기간 내 특이 공시 이력 없음"]

    # 4. 상태 객체에 주입
    state.qual = QualResult(
        score=int(parsed_result.get("score", 50)),
        sentiment=parsed_result.get("sentiment", "neutral"),
        event_types=parsed_result.get("event_types", []),
        evidence=parsed_result.get("evidence", []),
        risks=parsed_result.get("risks", [])
    )

    return state