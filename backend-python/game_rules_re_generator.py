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
    2222: { # 기존 규칙 생성 예시에서 나온 규칙 ID (만약 규칙이 DB에 저장된다면)
        "ruleId": 2222,
        "turnStructure": "1. 자원 수집 → 2. 행동 선택 → 3. 전투 또는 협상 → 4. 턴 종료 처리",
        "actionRules": [
            "자원 수집 시 무작위 카드 2장과 1 토큰 획득",
            "상대 진영과 협상 시 거래 조건을 비공개로 제안 가능",
            "전투 시 주사위로 결과 결정, 추가 카드 사용 가능"
        ],
        "victoryCondition": "유물을 3개 먼저 수집하면 즉시 승리",
        "penaltyRules": [
            "자원이 0일 때 행동 제한 발생",
            "동맹을 배신할 경우 다음 2턴간 협상 불가"
        ],
        "designNote": "게임 흐름이 직관적이면서도, 협상과 배신이 자연스럽게 녹아들도록 구조화함"
    },
    23: { # 요청하신 ruleId 23에 대한 예시 데이터
        "ruleId": 23,
        "turnStructure": "1. 플레이어 턴 시작 → 2. 이동 → 3. 행동 (자원 수집 또는 카드 사용) → 4. 턴 종료",
        "actionRules": [
            "이동: 자신의 미니어처를 인접한 공간으로 1칸 이동",
            "자원 수집: 현재 위치의 자원 타일에서 자원 토큰 1개 획득",
            "카드 사용: 손에서 카드 1장을 내어 효과 발동 (예: 추가 이동, 적 공격)"
        ],
        "victoryCondition": "맵 중앙에 위치한 보스 몬스터를 처치하면 승리",
        "penaltyRules": [
            "체력 0이 되면 모든 자원 상실 및 1턴 쉬기",
            "특정 이벤트 카드 발동 시 강제 이동"
        ],
        "designNote": "간단하고 빠른 턴 진행을 목표로 함"
    }
}


# -----------------------------------------------------------------------------
# 2. LLM 설정 및 프롬프트 정의 (게임 규칙 재생성)
# -----------------------------------------------------------------------------

llm_regenerate_rules = ChatOpenAI(model_name="gpt-4o", temperature=0.7) # 규칙 재생성은 창의성과 명확성 균형

# 게임 규칙 재생성을 위한 프롬프트 템플릿
regenerate_rules_prompt_template = PromptTemplate(
    input_variables=["original_rule_json", "feedback", "rule_id"],
    template="""당신은 보드게임 규칙 전문가입니다.
    주어진 기존 보드게임 규칙에 대한 사용자 피드백을 바탕으로,
    **기존 규칙을 수정하거나 완전히 새로운 규칙을 한국어로 생성**해주세요.
    특히 피드백의 내용을 적극적으로 반영해야 합니다.

    재생성된 규칙은 다음 형식으로 제공되어야 하며, ruleId는 기존의 ruleId를 그대로 사용합니다.

    ---
    **기존 보드게임 규칙 정보:**
    ```json
    {original_rule_json}
    ```

    **사용자 피드백:**
    {feedback}

    **기존 규칙 ID (재생성된 규칙에 동일하게 적용):**
    {rule_id}
    ---

    당신은 다음 JSON 형식으로만 응답해야 합니다. **다른 어떤 설명이나 추가적인 텍스트도 포함하지 마세요.**
    모든 내용은 **한국어**로 작성되어야 합니다.

    ```json
    {{
      "ruleId": {rule_id},
      "turnStructure": "[게임의 각 턴이 어떤 단계로 구성되는지 순서대로 설명 (예: 1. 자원 수집 → 2. 행동 선택 → 3. 전투 또는 협상 → 4. 턴 종료 처리)]",
      "actionRules": [
        "[플레이어가 턴에 할 수 있는 주요 행동 1에 대한 구체적인 규칙 (한국어)]",
        "[플레이어가 턴에 할 수 있는 주요 행동 2에 대한 구체적인 규칙 (한국어)]"
      ],
      "victoryCondition": "[게임의 최종 승리 조건 및 판정 방식 (한국어)]",
      "penaltyRules": [
        "[플레이어가 특정 상황에서 받게 되는 페널티 1 (한국어)]",
        "[플레이어가 특정 상황에서 받게 되는 페널티 2 (한국어)]"
      ],
      "designNote": "[게임 규칙 설계에 대한 간략한 디자이너 노트 또는 의도 설명 (한국어)]"
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

    original_rule_data = game_rules_database.get(rule_id_to_regenerate)
    if not original_rule_data:
        raise HTTPException(status_code=404, detail=f"Rule ID {rule_id_to_regenerate}에 해당하는 원본 규칙 데이터를 찾을 수 없습니다.")

    original_rule_json_str = json.dumps(original_rule_data, indent=2, ensure_ascii=False)

    try:
        response = regenerate_rules_chain.invoke({
            "original_rule_json": original_rule_json_str,
            "feedback": feedback,
            "rule_id": rule_id_to_regenerate
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 체인 실행 중 오류 발생: {e}")

    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            regenerated_rules = json.loads(json_str)

            # ruleId는 기존 것을 유지 (LLM이 잘못 생성해도 고정)
            regenerated_rules["ruleId"] = rule_id_to_regenerate
            
            return regenerated_rules
        else:
            raise ValueError("LLM 응답에서 유효한 JSON 블록을 찾을 수 없습니다.")

    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        print(f"LLM 응답 텍스트: {response['text']}")
        raise HTTPException(status_code=500, detail=f"LLM 응답을 JSON 형식으로 파싱할 수 없습니다: {e}. 원본 응답: {response['text']}")
    except ValueError as e:
        print(f"값 오류: {e}")
        print(f"LLM 응답 텍스트: {response['text']}")
        raise HTTPException(status_code=500, detail=str(e))
    except KeyError as e:
        print(f"필수 키가 LLM 응답에 없습니다: {e}")
        print(f"LLM 응답 텍스트: {response['text']}")
        raise HTTPException(status_code=500, detail=f"필수 키 '{e}'가 LLM 응답에 없습니다.")


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
