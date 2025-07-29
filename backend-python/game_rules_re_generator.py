import pandas as pd
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import datetime
import json
import re
import numpy as np
import os
from dotenv import load_dotenv

# FastAPI 관련 라이브러리
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 설정 (환경 변수에서 가져오기)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

app = FastAPI(
    title="보드게임 기획 API",
    description="보드게임 컨셉 생성, 재생성, 구성요소 생성, 규칙 생성 및 규칙 재생성 기능을 제공합니다.",
    version="1.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# 1. 가상의 데이터 저장소 (모든 기획 데이터 통합)
#    실제 서비스에서는 DB에서 데이터를 조회하는 로직으로 대체됩니다.
# -----------------------------------------------------------------------------
# 이 데이터베이스는 규칙 재생성 기능에서만 사용됩니다.
# 요청하신 ruleId: 23에 대한 예시 데이터를 추가합니다.
game_rules_database = {
    23: {
        "conceptId": 12, # 이 규칙이 conceptId 12와 연결되어 있음을 명시
        "rule": {
            "ruleId": 23,
            "turnStructure": "1. 플레이어 턴 시작 → 2. 이동 → 3. 행동 (자원 수집 또는 카드 사용) → 4. 턴 종료",
            "actionRules": [
                "이동: 자신의 미니어처를 인접한 공간으로 1칸 이동",
                "자원 수집: 현재 위치의 자원 타일에서 자원 토큰 1개 획득",
                "카드 사용: 손에서 카드 1장을 내어 효과 발동 (예: 추가 이동, 적 공격)"
            ],
            "victoryCondition": "맵 중앙에 위치한 보스 몬스터를 처치하면 승리",
            "penaltyRules": ["체력 0이 되면 모든 자원 상실 및 1턴 쉬기"],
            "designNote": "간단하고 빠른 턴 진행을 목표로 함"
        }
    }
}

# 게임 컨셉/세계관/목표 데이터 (이전과 동일, 컨텍스트 제공용)
concept_world_objective_database = {
    12: {
        "concept": {
            "theme": "SF 생존/전략",
            "mechanics": "자원 관리, 기지 건설, 타워 디펜스, 비대칭 능력, 협력/경쟁"
        },
        "world": {
            "storyline": "인류의 마지막 희망을 싣고 떠난 우주선 '아크론'은 미지의 행성 '제노스-7' 상공에서 파괴되었다."
        },
        "objective": {
            "mainGoal": "비상 신호 장치의 핵심 부품 3개를 모두 수리하여 구조 신호를 성공적으로 송신하면 승리합니다."
        }
    }
}


# -----------------------------------------------------------------------------
# 2. LLM 설정 및 프롬프트 정의 (게임 규칙 재생성)
# -----------------------------------------------------------------------------

llm_regenerate_rules = ChatOpenAI(model_name="gpt-4o", temperature=0.7)

# 게임 규칙 재생성을 위한 고도화된 프롬프트 템플릿
regenerate_rules_prompt_template = PromptTemplate(
    input_variables=["game_context", "original_rule_json", "feedback", "rule_id"],
    template="""
    # Mission: 당신은 플레이어의 피드백을 반영하여 게임의 깊이를 더하는 '리드 게임 밸런서'입니다. 당신의 임무는 기존 규칙의 문제점을 진단하고, 게임의 핵심 컨셉과 메커니즘을 바탕으로 규칙을 개선하여 더 풍부한 전략적 경험을 제공하는 것입니다.

    # Refinement Process:
    1.  **피드백 해석 (Interpret Feedback):** 사용자의 피드백 '{feedback}'의 근본적인 원인을 파악합니다. '행동이 단순하다'는 것은 '의미 있는 선택지가 부족하다'는 의미입니다.
    2.  **컨셉 연계 (Link to Concept):** 주어진 '게임 컨텍스트'의 핵심 메커니즘을 어떻게 더 잘 활용하여 피드백을 해결할지 고민합니다. 예를 들어, '자원 관리' 메커니즘이 있다면, 자원을 특별하게 소모하여 강력한 행동을 하는 규칙을 추가할 수 있습니다.
    3.  **규칙 재설계 (Redesign Rules):** 위의 분석을 바탕으로 'actionRules'를 중심으로 규칙을 재설계합니다. 기존 규칙을 개선하거나, 새로운 전략적 행동을 추가하여 더 다양한 플레이 스타일이 가능하도록 만듭니다.

    # Input Data:
    ---
    ### 1. Game Context (For a Deeper Understanding):
    {game_context}

    ### 2. Original Rules (To be Improved):
    ```json
    {original_rule_json}
        ```

    ### 3. User Feedback to Reflect:
    {feedback}

    **기존 규칙 ID (재생성된 규칙에 동일하게 적용):**
    {rule_id}
    ---


    Final Output Instruction:
    이제, 위의 모든 지침과 과정을 따라 아래 JSON 형식에 맞춰 '재생성된 전체 규칙'만을 생성해주세요.
    JSON 코드 블록 외에 어떤 인사, 설명, 추가 텍스트도 절대 포함해서는 안 됩니다.
    당신은 다음 JSON 형식으로만 응답해야 합니다. **다른 어떤 설명이나 추가적인 텍스트도 포함하지 마세요.**
    모든 내용은 **한국어**로 작성되어야 합니다.

    ```json
    {{
    "ruleId": {rule_id},
    "turnStructure": "[개선된 게임 흐름에 맞는 새로운 턴 구조. 더 역동적으로 변경될 수 있음]",
    "actionRules": [
        "[피드백을 반영하여 더 다양하고 전략적인 선택지를 제공하는 행동 규칙 1]",
        "[새롭게 추가되거나 흥미롭게 변경된 행동 규칙 2]"
    ],
    "victoryCondition": "[기존 승리 조건을 유지하되, 더 명확하게 서술]",
    "penaltyRules": [
        "[게임의 복잡도에 맞게 수정되거나 추가된 페널티 규칙]"
    ],
    "designNote": "[피드백을 어떻게 반영했고, 새로운 규칙이 어떻게 게임의 전략적 깊이를 더하는지에 대한 구체적인 설명]"
    }}
    ```
    """
)
regenerate_rules_chain = LLMChain(llm=llm_regenerate_rules, prompt=regenerate_rules_prompt_template)



# -----------------------------------------------------------------------------
# 3. 게임 규칙 재생성 함수
# -----------------------------------------------------------------------------
def regenerate_game_rules_logic(request_data: dict) -> dict:
    rule_id_to_regenerate = request_data.get("ruleId")
    feedback = request_data.get("feedback", "")

    # 1. 원본 규칙 및 연관 컨셉 ID 조회
    original_rule_entry = game_rules_database.get(rule_id_to_regenerate)
    if not original_rule_entry:
        raise HTTPException(status_code=404, detail=f"Rule ID {rule_id_to_regenerate}에 해당하는 원본 규칙 데이터를 찾을 수 없습니다.")
    
    original_rule_data = original_rule_entry.get("rule")
    concept_id = original_rule_entry.get("conceptId")

    # 2. 연관된 게임 컨셉/목표 정보 조회 (중요!)
    game_context = concept_world_objective_database.get(concept_id)
    if not game_context:
        raise HTTPException(status_code=404, detail=f"연관된 Concept ID {concept_id}의 게임 정보를 찾을 수 없습니다.")

    # 3. LLM에 전달할 정보 가공
    game_context_summary = f"""
    - 테마: {game_context.get("concept", {}).get("theme", "N/A")}
    - 핵심 메커니즘: {game_context.get("concept", {}).get("mechanics", "N/A")}
    - 최종 목표: {game_context.get("objective", {}).get("mainGoal", "N/A")}
    """
    original_rule_json_str = json.dumps(original_rule_data, indent=2, ensure_ascii=False)

    # 4. LLM Chain 호출
    try:
        response = regenerate_rules_chain.invoke({
            "game_context": game_context_summary.strip(),
            "original_rule_json": original_rule_json_str,
            "feedback": feedback,
            "rule_id": rule_id_to_regenerate
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 체인 실행 중 오류 발생: {e}")

    # 5. LLM 응답 파싱 및 DB 업데이트
    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)
        if not json_match:
            raise ValueError("LLM 응답에서 유효한 JSON 블록을 찾을 수 없습니다.")

        json_str = json_match.group(1)
        regenerated_rules = json.loads(json_str)
        regenerated_rules["ruleId"] = rule_id_to_regenerate # ID는 기존 값으로 고정

        # 메모리 내 DB 업데이트
        game_rules_database[rule_id_to_regenerate]["rule"] = regenerated_rules
        print(f"Rule ID {rule_id_to_regenerate}가 새로운 규칙으로 업데이트되었습니다.")
        
        return regenerated_rules
    except (json.JSONDecodeError, ValueError) as e:
        # ... (기존 에러 처리 로직)
        raise HTTPException(status_code=500, detail=f"LLM 응답 파싱 오류: {e}")
# -----------------------------------------------------------------------------
# 4. FastAPI 엔드포인트 정의 (게임 규칙 재생성)
# -----------------------------------------------------------------------------

# 요청 바디를 위한 Pydantic 모델 정의
class RegenerateRulesRequest(BaseModel):
    ruleId: int = Field(..., example=23, description="재생성할 원본 규칙의 ID")
    feedback: str = Field(..., example="행동이 너무 단순한 것 같아요. 좀 더 다양한 전략이 있었으면 해요.", description="규칙 재생성을 위한 사용자 피드백")

# 응답 바디를 위한 Pydantic 모델 정의 (규칙 형식과 동일)
class RegeneratedRulesResponse(BaseModel):
    ruleId: int
    turnStructure: str
    actionRules: List[str]
    victoryCondition: str
    penaltyRules: List[str]
    designNote: str

# API 엔드포인트: 게임 규칙 재생성
@app.post("/api/plans/regenerate-rule", response_model=RegeneratedRulesResponse, summary="게임 규칙 재생성 (피드백 반영)")
async def regenerate_rules_api_endpoint(request: RegenerateRulesRequest):
    """
    주어진 `ruleId`와 `feedback`을 바탕으로 기존 게임 규칙을 재생성합니다.
    """
    try:
        regenerated_rules = regenerate_game_rules_logic(request.dict())
        return regenerated_rules
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류 발생: {e}")


# -----------------------------------------------------------------------------
# 5. (선택 사항) 기존 기능 관련 코드 (필요시 주석 해제하여 사용)
#    실제 앱에서는 이전에 제공했던 모든 기능의 코드가 이 파일에 포함되어야 합니다.
#    간결함을 위해 본 예시에서는 관련 데이터베이스, LLM 체인, 함수, 엔드포인트 코드를 주석 처리합니다.
# -----------------------------------------------------------------------------

# # 컨셉 데이터 (기존 생성/재생성에 사용)
# concept_database_for_regen = { ... } # 위에서 정의된 것과 동일하게 유지

# # 기획안 ID에 따른 상세 정보 (컨셉, 세계관, 목표 등 - 목표, 구성요소, 규칙 생성에 사용)
# concept_world_objective_database = { ... } # 위에서 정의된 것과 동일하게 유지

# # planId 기반 데이터베이스 (구성요소 생성에 사용)
# plan_data_for_components = { ... } # 위에서 정의된 것과 동일하게 유지

# # -- 컨셉 생성 관련 LLM 및 엔드포인트 --
# # from langchain_community.vectorstores import FAISS
# # from langchain_openai import OpenAIEmbeddings
# # embeddings = OpenAIEmbeddings()
# # faiss_index_path = "faiss_boardgame_index"
# # vectorstore = None # Load FAISS here or create
# # retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) if vectorstore else None
# # llm_generate = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
# # generate_concept_prompt_template = PromptTemplate( ... )
# # concept_generation_chain = LLMChain(llm=llm_generate, prompt=generate_concept_prompt_template)
# #
# # class BoardgameConceptRequest(BaseModel): ...
# # class BoardgameConceptResponse(BaseModel): ...
# #
# # @app.post("/generate-concept", response_model=BoardgameConceptResponse, summary="새로운 보드게임 컨셉 생성")
# # async def generate_boardgame_concept_api(user_input: BoardgameConceptRequest): ...

# # -- 컨셉 재생성 관련 LLM 및 엔드포인트 --
# # (이 파일 상단에 이미 정의되어 있습니다)
# # llm_regenerate = ChatOpenAI(model_name="gpt-4o", temperature=0.9)
# # regenerate_concept_prompt_template = PromptTemplate( ... )
# # regenerate_concept_chain = LLMChain(llm=llm_regenerate, prompt=regenerate_concept_prompt_template)
# # class RegenerateConceptRequest(BaseModel): ...
# # class RegeneratedConceptResponse(BaseModel): ...
# # @app.post("/api/plans/regenerate-concept", response_model=RegeneratedConceptResponse, summary="기존 보드게임 컨셉 재생성 (피드백 반영)")
# # async def regenerate_concept_api_endpoint(request: RegenerateConceptRequest): ...


# # -- 게임 목표 생성 관련 LLM 및 엔드포인트 --
# # llm_objective = ChatOpenAI(model_name="gpt-4o", temperature=0.7)
# # game_objective_prompt_template = PromptTemplate( ... )
# # game_objective_chain = LLMChain(llm=llm_objective, prompt=game_objective_prompt_template)
# # class GameObjectiveRequest(BaseModel): ...
# # class GameObjectiveResponse(BaseModel): ...
# # @app.post("/generate-objective", response_model=GameObjectiveResponse, summary="게임 목표 생성")
# # async def generate_objective_api(request: GameObjectiveRequest): ...

# # -- 구성요소 생성 관련 LLM 및 엔드포인트 --
# # llm_components = ChatOpenAI(model_name="gpt-4o", temperature=0.7)
# # component_generation_prompt_template = PromptTemplate( ... )
# # component_generation_chain = LLMChain(llm=llm_components, prompt=component_generation_prompt_template)
# # class GenerateComponentsRequest(BaseModel): ...
# # class ComponentItem(BaseModel): ...
# # class GenerateComponentsResponse(BaseModel): ...
# # @app.post("/generate-components", response_model=GenerateComponentsResponse, summary="컨셉/목표 기반 구성요소 생성")
# # async def generate_components_api(request: GenerateComponentsRequest): ...

# # -- 게임 규칙 생성 관련 LLM 및 엔드포인트 --
# # llm_rules = ChatOpenAI(model_name="gpt-4o", temperature=0.6)
# # game_rules_prompt_template = PromptTemplate( ... )
# # game_rules_chain = LLMChain(llm=llm_rules, prompt=game_rules_prompt_template)
# # class GenerateRulesRequest(BaseModel): ...
# # class GenerateRulesResponse(BaseModel): ...
# # @app.post("/generate-rules", response_model=GenerateRulesResponse, summary="컨셉/목표 기반 게임 규칙 생성")
# # async def generate_rules_api(request: GenerateRulesRequest): ...
