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
    description="보드게임 컨셉 생성, 재생성, 구성요소 생성 및 규칙 생성 기능을 제공합니다.",
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
# 1. 가상의 컨셉, 세계관, 게임 목표 데이터 저장소
#    (실제 서비스에서는 DB나 파일에서 데이터를 조회하는 로직으로 대체됩니다.)
#    conceptId를 키로 하여 관련 데이터를 매핑합니다.
# -----------------------------------------------------------------------------
concept_world_objective_database = {
    1001: {
        "concept": {
            "conceptId": 1001,
            "planId": 2001,
            "theme": "전략",
            "playerCount": "2~4명",
            "averageWeight": 3.0,
            "ideaText": "플레이어는 전략적인 지형을 활용해 상대를 견제하는 턴제 전투를 벌입니다. 각 라운드마다 새로운 카드를 드래프트하여 유닛을 소환하고, 영토를 확장하며 자원을 확보해야 합니다.",
            "mechanics": "지역 점령, 카드 드래프트, 핸드 매니지먼트, 자원 관리",
            "storyline": "고대 제국의 후예들이 전설의 유물을 차지하기 위해 맞붙는다. 사막의 모래폭풍, 숲의 맹수, 얼어붙은 산맥 등 다양한 지형이 전투에 영향을 미치며, 각 가문은 고유한 능력을 활용해 승리를 쟁취해야 한다.",
            "createdAt": "2025-07-24T15:00:00"
        },
        "world": {
            "storyline": "오랜 전쟁으로 황폐해진 대륙에 고대 제국의 마지막 유물 '에테르 크리스탈'이 발견되었다. 이 크리스탈을 차지하는 자가 대륙의 패권을 쥐게 될 것이다. 각 가문은 전설 속 유물을 찾아 전쟁을 시작한다.",
            "setting": { "era": "고대 제국 멸망 500년 후", "location": "파멸의 대륙 아르카디아", "factions": ["검은 독수리 가문", "황금 사자 가문", "하얀 늑대 가문"], "conflict": "에테르 크리스탈을 둘러싼 세력 간의 영토 및 자원 쟁탈전" },
            "tone": "전략적 경쟁 / 영토 확장"
        },
        "objective": {
            "mainGoal": "고대 제국의 유물 '에테르 크리스탈' 3개를 먼저 수집하는 가문이 승리합니다.",
            "subGoals": [
                "매 턴 시작 시 본인 영토에 비어있는 크리스탈 지대 1곳당 추가 자원 획득",
                "상대 가문의 본거지 점령 시 특별 유닛 소환 권한 획득"
            ],
            "winConditionType": "목표 달성형",
            "designNote": "영토 확장을 통한 자원 확보와 전략적인 유물 수집을 유도하며, 직접적인 전투로 인한 재미를 추구합니다."
        }
    },
    1002: {
        "concept": {
            "conceptId": 1002,
            "planId": 2002,
            "theme": "탐험",
            "playerCount": "1~2명",
            "averageWeight": 4.0,
            "ideaText": "플레이어는 미지의 행성을 탐험하며 위험한 외계 생명체와 맞서 싸우고, 고대 유적의 비밀을 파헤쳐야 합니다. 자원 수집과 장비 업그레이드를 통해 생존하며 탐험 목표를 달성하세요.",
            "mechanics": "덱 빌딩, 타일 놓기, 주사위 굴림, 협동",
            "storyline": "인류는 지구 자원 고갈로 인해 새로운 행성을 찾아 우주로 향한다. 하지만 도착한 행성은 숨겨진 생명체와 위험이 도사리고 있는 미지의 영역이었다. 플레이어는 각자 생존을 위해 팀을 꾸리고, 제한된 자원을 두고 다른 팀과 협상하거나 배신하며 살아남아야 한다.",
            "createdAt": "2025-07-24T16:00:00"
        },
        "world": {
            "storyline": "인류는 멸망의 위기에 처했고, 마지막 희망은 '크세논'이라 불리는 미지의 행성뿐이었다. 하지만 크세논은 겉보기와 달리 고대 문명의 잔해와 치명적인 외계 생명체, 그리고 알 수 없는 에너지장이 뒤덮인 곳이었다. 탐사팀은 생존과 함께 행성의 비밀을 파헤쳐야 한다.",
            "setting": { "era": "2242년", "location": "행성 크세논", "factions": ["지구 탐사대", "선구자 유물 수집가", "크세논 토착 생명체"], "conflict": "혹독한 환경에서의 생존 및 행성 크세논의 고대 비밀 해독" },
            "tone": "긴장감 있는 생존 / 미스터리 탐험"
        },
        "objective": {
            "mainGoal": "행성 크세논의 핵심 유물 5개를 모두 활성화하고 탈출선을 수리하여 행성을 떠나는 것이 주요 목표입니다.",
            "subGoals": [
                "매 턴 새로운 타일을 탐험하여 미지의 지역을 개척하고 보상 획득",
                "위험한 외계 생명체를 물리치고 희귀 자원을 수집하여 장비 업그레이드"
            ],
            "winConditionType": "목표 달성형",
            "designNote": "협동 플레이와 자원 관리의 중요성을 강조하며, 탐험의 재미와 미지의 위협을 동시에 제공합니다."
        }
    },
    12: { # 요청하신 conceptId 12의 예시 데이터
        "concept": {
            "conceptId": 12,
            "planId": 3001,
            "theme": "SF 생존/전략",
            "playerCount": "2~4명",
            "averageWeight": 3.5,
            "ideaText": "알 수 없는 외계 행성에 불시착한 생존자들이 제한된 자원을 활용하여 기지를 건설하고, 위험한 환경과 외계 생명체로부터 자신을 방어하며 탈출을 시도하는 협력 및 경쟁 게임입니다. 플레이어는 서로 협력하며 자원을 공유할 수도 있고, 배신하여 다른 팀의 자원을 빼앗을 수도 있습니다.",
            "mechanics": "자원 관리, 기지 건설, 타워 디펜스, 비대칭 능력, 협력/경쟁",
            "storyline": "지구의 자원 고갈로 인해 새로운 정착지를 찾아 우주선을 타고 떠난 인류. 예상치 못한 소행성 충돌로 미지의 행성에 불시착하게 된다. 이 행성은 아름답지만 치명적인 환경과 지능적인 외계 생명체가 서식하고 있었는데...",
            "createdAt": "2025-07-25T10:00:00"
        },
        "world": {
            "storyline": "인류의 마지막 희망을 싣고 떠난 우주선 '아크론'은 미지의 행성 '제노스-7' 상공에서 파괴되었다. 소수의 생존자들은 행성 표면에 불시착했지만, 제노스-7은 붉은 먼지 폭풍과 기이한 식물, 그리고 지저분한 '코랄'이라 불리는 외계 생명체들로 가득한 지옥이었다. 생존자들은 파편화된 비상 신호 장치를 재조립하여 구조 신호를 보내고, 그 전까지 행성의 위협으로부터 버텨내야 한다.",
            "setting": { "era": "2350년, 포스트-아포칼립스 우주", "location": "행성 제노스-7의 '붉은 황무지'", "factions": ["아크론 잔존 생존자", "행성 토착 코랄 종족", "미지의 고대 기계 지성체"], "conflict": "구조 신호 송신을 위한 자원 확보 및 외계 환경과 생명체로부터의 생존" },
            "tone": "절망적 생존 / 협력과 배신"
        },
        "objective": {
            "mainGoal": "비상 신호 장치의 핵심 부품 3개를 모두 수리하여 구조 신호를 성공적으로 송신하면 승리합니다.",
            "subGoals": [
                "매 턴 특정 자원 건물 건설 시 추가 방어 보너스 획득",
                "특정 외계 생명체 보스 처치 시 희귀 업그레이드 아이템 획득"
            ],
            "winConditionType": "목표 달성형",
            "designNote": "생존을 위한 기지 건설과 자원 관리가 중요하며, 협력과 경쟁 요소가 적절히 섞여 긴장감을 유발합니다."
        }
    }
}

# -----------------------------------------------------------------------------
# 2. LLM 설정 및 프롬프트 정의
# -----------------------------------------------------------------------------

llm_rules = ChatOpenAI(model_name="gpt-4o", temperature=0.6) # 규칙은 더 명확해야 하므로 temperature를 낮춤

# 게임 규칙 설계를 위한 프롬프트 템플릿
# 게임 규칙 설계를 위한 프롬프트 템플릿 - 역할, 원칙, 구조를 강화하여 AI 성능 극대화
game_rules_prompt_template = PromptTemplate(
    input_variables=["theme", "playerCount", "averageWeight", "ideaText", "mechanics",
                     "storyline", "world_setting", "world_tone",
                     "mainGoal", "subGoals", "winConditionType", "objective_designNote"],
    template="""
# Mission: 당신은 복잡한 게임 컨셉을 플레이어가 쉽게 배우고 깊이 즐길 수 있는, 명확하고 완결성 있는 규칙으로 만드는 '리드 룰(Rule) 디자이너'입니다. 당신의 임무는 주어진 게임의 모든 기획 정보를 종합하여, 게임의 준비부터 종료까지 모든 과정을 아우르는 완전한 게임 규칙서를 설계하는 것입니다.

# Key Principles of Rule Design:
1.  **메커니즘의 구체화 (Mechanics to Actions):** '주요 메커니즘'({mechanics}) 목록을 보고, 각 메커니즘을 플레이어가 수행할 수 있는 구체적인 '행동 규칙(actionRules)'으로 변환해야 합니다. 예를 들어, 메커니즘이 '지역 점령'이라면, '내 유닛을 인접한 빈 지역으로 이동시켜 점령한다'와 같은 행동 규칙을 만들어야 합니다.
2.  **완결성 있는 구조 (Complete Structure):** 규칙은 단순히 행동의 나열이 아닙니다. 게임 시작을 위한 '준비 단계'는 없지만, 게임의 흐름인 '턴 구조(turnStructure)', 구체적인 '행동 규칙(actionRules)', 그리고 '승리 조건(victoryCondition)'이 명확하게 포함되어야 합니다.
3.  **명확성과 예외 처리 (Clarity & Edge Cases):** 모든 규칙은 애매함 없이 명확해야 합니다. 또한, 게임 중 발생할 수 있는 부정적인 상황이나 규칙 위반 시 적용될 '페널티 규칙(penaltyRules)'을 반드시 포함하여 규칙의 허점을 보완해야 합니다.

# Input Data Analysis:
---
### 보드게임 종합 정보:
-   **핵심 컨셉:** {ideaText}
-   **주요 메커니즘:** {mechanics}
-   **핵심 목표:** {mainGoal} (승리 조건 유형: {winConditionType})
-   **세계관 및 스토리:** {storyline}, {world_setting}
-   **게임 분위기:** {world_tone}
---

# Final Output Instruction:
이제, 위의 모든 지침과 원칙을 따라 아래 JSON 형식에 맞춰 최종 결과물만을 생성해주세요.
**JSON 코드 블록 외에 어떤 인사, 설명, 추가 텍스트도 절대 포함해서는 안 됩니다.**
모든 내용은 **누가 읽어도 이해하기 쉬운 한국어**로 작성되어야 합니다.

```json
{{
  "ruleId": [임의의 고유한 정수 ID],
  "turnStructure": "[한 플레이어의 턴이 어떤 단계(Phase)로 구성되는지 순서대로 설명. 예: 1.자원 수집 -> 2.액션 수행 -> 3.정리]",
  "actionRules": [
    "[플레이어가 턴에 할 수 있는 주요 행동 1에 대한 구체적인 규칙. (어떤 자원을 소모하고, 어떤 결과를 얻는지 명확하게 설명)]",
    "[플레이어가 턴에 할 수 있는 주요 행동 2에 대한 구체적인 규칙. (메커니즘을 구체적인 행동으로 변환)]"
  ],
  "victoryCondition": "[게임의 최종 승리 조건을 명확하게 서술. 게임 목표의 'mainGoal'과 'winConditionType'을 구체적인 규칙으로 변환하여, 언제, 어떻게 승리 판정을 하는지 설명]",
  "penaltyRules": [
    "[플레이어가 특정 상황에서 받게 되는 페널티 1. (예: 자원 부족, 특정 행동 실패 시)]",
    "[플레이어가 특정 상황에서 받게 되는 페널티 2. (예: 동맹 배신, 금지된 행동 시도 시)]"
  ],
  "designNote": "[이 규칙들이 어떻게 게임의 핵심 재미(예: 전략적 깊이, 플레이어 간 상호작용)를 만들어내는지에 대한 설계 의도 설명]"
}}
    ```
    """
)
game_rules_chain = LLMChain(llm=llm_rules, prompt=game_rules_prompt_template)

# -----------------------------------------------------------------------------
# 3. 게임 규칙 생성 함수 (FastAPI 통합을 위해 수정)
# -----------------------------------------------------------------------------

def generate_game_rules_logic(concept_id: int) -> dict:
    """
    주어진 conceptId에 해당하는 보드게임 컨셉, 세계관, 게임 목표를 바탕으로 게임 규칙을 생성합니다.
    """
    # 1. 컨셉, 세계관, 게임 목표 데이터 조회
    data_entry = concept_world_objective_database.get(concept_id)
    if not data_entry:
        raise HTTPException(status_code=404, detail=f"Concept ID {concept_id}에 해당하는 데이터를 찾을 수 없습니다.")

    concept_data = data_entry.get("concept", {})
    world_data = data_entry.get("world", {})
    objective_data = data_entry.get("objective", {})

    # 세계관 설정 부분을 문자열로 변환 (중첩된 딕셔너리이므로 필요)
    world_setting_str = json.dumps(world_data.get("setting", {}), ensure_ascii=False) if world_data.get("setting") else ""

    # 보조 목표 리스트를 문자열로 변환 (프롬프트에 리스트를 직접 넣기 어려울 수 있어 변환)
    sub_goals_str = ", ".join(objective_data.get("subGoals", []))

    # 2. LLM Chain 호출
    try:
        response = game_rules_chain.invoke({
            "theme": concept_data.get("theme", ""),
            "playerCount": concept_data.get("playerCount", ""),
            "averageWeight": concept_data.get("averageWeight", 0.0),
            "ideaText": concept_data.get("ideaText", ""),
            "mechanics": concept_data.get("mechanics", ""),
            "storyline": concept_data.get("storyline", ""),
            "world_setting": world_setting_str,
            "world_tone": world_data.get("tone", ""),
            "mainGoal": objective_data.get("mainGoal", ""),
            "subGoals": sub_goals_str,
            "winConditionType": objective_data.get("winConditionType", ""),
            "objective_designNote": objective_data.get("designNote", "")
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 체인 실행 중 오류 발생: {e}")

    # 3. LLM 응답 파싱 및 후처리
    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)

        if json_match:
            json_str = json_match.group(1)
            game_rules = json.loads(json_str)

            # ruleId가 없거나 유효하지 않으면 임의로 할당
            if not isinstance(game_rules.get("ruleId"), int):
                # 타임스탬프를 기반으로 간단한 고유 ID 생성
                game_rules["ruleId"] = int(datetime.datetime.now().timestamp() * 1000) % 1000000 + 1000 # 1000 이상

            return game_rules
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
# 4. FastAPI 엔드포인트 정의 (게임 규칙 생성)
# -----------------------------------------------------------------------------

# 요청 바디를 위한 Pydantic 모델 정의
class GenerateRulesRequest(BaseModel):
    conceptId: int = Field(..., example=12, description="게임 규칙을 생성할 컨셉의 ID")

# 응답 바디를 위한 Pydantic 모델 정의 (요청된 출력 형식에 맞춤)
class GenerateRulesResponse(BaseModel):
    ruleId: int
    turnStructure: str
    actionRules: List[str]
    victoryCondition: str
    penaltyRules: List[str]
    designNote: str

# API 엔드포인트: 게임 규칙 생성
@app.post("/api/plans/generate-rule", response_model=GenerateRulesResponse, summary="컨셉/목표 기반 게임 규칙 생성")
async def generate_rules_api(request: GenerateRulesRequest):
    """
    주어진 `conceptId`에 해당하는 보드게임의 컨셉, 세계관, 목표를 바탕으로 게임 규칙을 생성합니다.
    """
    try:
        game_rules_data = generate_game_rules_logic(request.conceptId)
        return game_rules_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류 발생: {e}")


# -----------------------------------------------------------------------------
# 5. (선택 사항) 기존 컨셉 생성, 재생성, 구성요소 생성 관련 코드 (간결함을 위해 생략 가능)
#    실제 프로젝트에서는 별도의 모듈로 분리하는 것이 좋습니다.
#    이전에 제공했던 다른 엔드포인트를 이 파일에 포함하려면 아래와 같이 추가할 수 있습니다.
# -----------------------------------------------------------------------------
# # 가상의 컨셉 데이터 저장소 (재생성 대상이 되는 원본 컨셉 포함)
# # 이 데이터베이스는 위의 concept_world_objective_database와 통합되거나 별도 관리 필요
# concept_database_regen = {
#     1001: { "conceptId": 1001, "planId": 2001, "theme": "전략", ... },
#     # ...
# }
#
# llm_regenerate = ChatOpenAI(model_name="gpt-4o", temperature=0.9)
# # regenerate_concept_prompt_template 및 regenerate_concept_chain 정의
# # regenerate_board_game_concept 함수 정의
#
# @app.post("/regenerate-concept", response_model=RegeneratedConceptResponse, summary="기존 보드게임 컨셉 재생성 (피드백 반영)")
# async def regenerate_concept_api_endpoint(request: RegenerateConceptRequest):
#     # ... regenerate_board_game_concept 호출 로직
#     pass
#
# # RAG를 위한 컨셉 생성 관련 코드 (FAISS, Embeddings 등)
# # ...
# llm_generate = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
# # generate_concept_prompt_template 및 concept_generation_chain 정의
#
# @app.post("/generate-concept", response_model=BoardgameConceptResponse, summary="새로운 보드게임 컨셉 생성")
# async def generate_boardgame_concept_api(user_input: BoardgameConceptRequest):
#     # ... 컨셉 생성 로직
#     pass
#
# # 구성요소 생성을 위한 데이터베이스 및 LLM 체인
# # ... (위의 concept_and_goal_database와 통합)
# llm_components = ChatOpenAI(model_name="gpt-4o", temperature=0.7)
# # component_generation_prompt_template 및 component_generation_chain 정의
# # generate_game_components_logic 함수 정의
#
# @app.post("/generate-components", response_model=GenerateComponentsResponse, summary="컨셉/목표 기반 구성요소 생성")
# async def generate_components_api(request: GenerateComponentsRequest):
#     # ... generate_game_components_logic 호출 로직
#     pass
