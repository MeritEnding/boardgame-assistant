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
from typing import List, Optional # List 추가

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 설정 (환경 변수에서 가져오기)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

app = FastAPI(
    title="보드게임 기획 API",
    description="보드게임 컨셉 생성, 재생성 및 구성요소 생성 기능을 제공합니다.",
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
# 1. 가상의 컨셉, 세계관, 목표 데이터 저장소
#    (실제 서비스에서는 DB나 파일에서 데이터를 조회하는 로직으로 대체됩니다.)
#    planId를 키로 하여 컨셉, 세계관, 목표 데이터를 매핑합니다.
# -----------------------------------------------------------------------------
concept_and_goal_database = {
    2001: { # planId 2001에 해당하는 데이터
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
        "objective": { # 가상 목표 데이터
            "mainGoal": "각 가문의 수장이 되어 에테르 크리스탈을 먼저 확보하고 대륙의 3개 주요 거점을 점령하십시오.",
            "subGoals": ["희귀 자원 채집", "고대 유적 탐험"],
            "winConditionType": "목표 달성형",
            "designNote": "영토 확장과 자원 관리에 전략적 깊이를 더해 플레이어 간의 경쟁을 유도합니다."
        }
    },
    2002: { # planId 2002에 해당하는 데이터
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
        "objective": { # 가상 목표 데이터
            "mainGoal": "행성 크세논의 중심부에 도달하여 고대 문명의 슈퍼컴퓨터를 활성화하고 탈출 신호를 보내십시오.",
            "subGoals": ["특정 유물 5개 수집", "희귀 생명체 3종 연구"],
            "winConditionType": "목표 달성형",
            "designNote": "제한된 자원과 미지의 위험 속에서 효율적인 탐험 경로를 선택하는 것이 중요합니다."
        }
    },
    3001: { # planId 3001에 해당하는 데이터 (conceptId 12)
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
        "objective": { # 가상 목표 데이터
            "mainGoal": "행성의 에너지 코어를 활성화하여 구조 신호를 송신하고, 탈출선이 도착할 때까지 생존하십시오.",
            "subGoals": ["행성 지도 100% 탐험", "외계 생명체 둥지 3개 파괴", "고급 기지 방어 시스템 구축"],
            "winConditionType": "생존/목표 달성형",
            "designNote": "플레이어 간의 협력과 개인의 생존 전략이 동시에 요구되는 긴장감 있는 게임을 목표로 합니다."
        }
    },
    # 사용자 요청의 planId: 1012에 해당하는 예시 데이터를 추가합니다.
    1012: {
        "concept": {
            "conceptId": 9999, # 임시 ID
            "planId": 1012,
            "theme": "시간 여행 판타지",
            "playerCount": "2~4명",
            "averageWeight": 3.8,
            "ideaText": "시간을 조작하여 과거와 미래를 넘나들며 역사적 사건의 변칙을 바로잡는 게임입니다. 플레이어는 시간 조작 능력을 활용해 퍼즐을 풀고, 적을 따돌리며, 숨겨진 진실을 밝혀야 합니다.",
            "mechanics": "시간 조작, 퍼즐 해결, 핸드 매니지먼트, 경로 만들기",
            "storyline": "시간의 강이 뒤틀리며 과거의 사건들이 예측 불가능하게 변하기 시작했습니다. '시간 수호자'들은 시간의 흐름을 원래대로 되돌리기 위해 시간 조각을 모으고, 역사적 변칙점을 찾아 수정해야 합니다. 하지만 시간의 균열 속에서 미지의 존재들이 그들을 방해합니다.",
            "createdAt": "2025-07-28T14:00:00"
        },
        "world": {
            "storyline": "우주 전체의 시간을 관장하는 신비로운 존재 '크로노스'가 잠들면서, 그의 힘이 약해져 시공간에 균열이 발생하기 시작했다. 이 균열을 통해 과거와 미래의 파편들이 현재로 흘러들어와 역사를 뒤흔들고 있다. 시간 수호자들은 크로노스의 마지막 숨결이 깃든 '시간의 흐름'을 복구하기 위해 위험한 여정을 시작한다.",
            "setting": {
                "era": "초월적인 시간",
                "location": "시간의 강, 과거와 미래의 주요 역사적 지점들",
                "factions": ["시간 수호자", "시간의 변칙", "기생 시간체"],
                "conflict": "역사 복구 vs 시간의 파괴"
            },
            "tone": "신비로운 / 시간 기반 퍼즐 / 모험"
        },
        "objective": {
            "mainGoal": "시간의 강에 흩어진 5개의 '크로노스 코어'를 모두 수집하여 시간의 흐름을 안정화하고, 역사를 원래대로 되돌리십시오.",
            "subGoals": ["특정 시대의 역사적 변칙 3가지 수정", "시간 조작 능력을 최대로 업그레이드", "시간의 균열 10개 봉인"],
            "winConditionType": "목표 달성형 / 퍼즐 해결형",
            "designNote": "시간의 흐름을 읽고 과거와 미래의 사건에 개입하는 전략적인 선택이 중요하며, 플레이어 간의 정보 공유와 협력이 필수적입니다."
        }
    }
}


# -----------------------------------------------------------------------------
# 2. LLM 설정 및 프롬프트 정의 (구성요소 생성)
# -----------------------------------------------------------------------------

llm_components = ChatOpenAI(model_name="gpt-4o", temperature=0.7) # 구체적인 구성요소는 명확해야 하므로 temperature 낮춤

# 구성요소 생성을 위한 프롬프트 템플릿
component_generation_prompt_template = PromptTemplate(
    input_variables=["theme", "playerCount", "averageWeight", "ideaText", "mechanics", "storyline", "mainGoal", "winConditionType", "world_setting", "world_tone"],
    template="""
    # Mission: 당신은 추상적인 게임 컨셉을 만질 수 있는 '제품'으로 구현하는 '리드 컴포넌트 전략가'입니다. 당신의 임무는 주어진 게임의 모든 정보(컨셉, 세계관, 목표)를 종합적으로 분석하여, 게임 플레이를 가능하게 하고 플레이어의 몰입감을 극대화하는 핵심 구성요소(컴포넌트) 목록을 설계하는 것입니다.

    # Component Design Philosophy:
    1.  **기능성 (Functionality):** 모든 구성요소는 반드시 게임의 핵심 메커니즘이나 목표 달성과 직접적으로 연결되어야 합니다. "왜 이 컴포넌트가 꼭 필요한가?"라는 질문에 답할 수 있어야 합니다.
    2.  **테마성 (Thematic Resonance):** 구성요소의 이름과 역할(effect)은 게임의 세계관과 스토리에 깊이 몰입하게 만드는 장치입니다. '자원 토큰' 대신 '에테르 조각'처럼 테마에 맞는 이름을 부여하세요.
    3.  **직관성 (Intuitive UX):** 플레이어가 구성요소를 보고 그 역할과 사용법을 쉽게 이해할 수 있어야 합니다. 'effect' 설명 시, 플레이어의 행동 관점에서 구체적으로 서술해주세요.

    # Input Data Analysis:
    ---
    **보드게임 종합 정보:**
    -   컨셉: {ideaText}
    -   메커니즘: {mechanics}
    -   주요 목표: {mainGoal}
    -   승리 조건: {winConditionType}
    -   세계관: {world_setting}, {storyline}
    -   전체적인 톤: {world_tone}
    ---

    # Final Output Instruction:
    이제, 위의 모든 지침과 철학을 따라 아래 JSON 형식에 맞춰 최종 결과물만을 생성해주세요.
    최소 5개 이상의 '핵심' 구성요소를 제안하되, 게임에 필요한 다양한 종류(보드, 카드, 토큰 등)를 균형 있게 포함해주세요.
    **JSON 코드 블록 외에 어떤 인사, 설명, 추가 텍스트도 절대 포함해서는 안 됩니다.**

    ```json
    {{
    "components": [
        {{
        "type": "[구성요소의 종류 (예: 게임 보드, 캐릭터 시트, 이벤트 카드, 자원 토큰, 목표 타일, 주사위 등)]",
        "name": "[세계관에 몰입감을 더하는 고유한 이름 (한국어)]",
        "effect": "[이 구성요소의 '게임플레이 기능'을 설명. 플레이어는 이걸로 무엇을 할 수 있고, 게임 목표 달성에 어떤 영향을 미치는지 구체적으로 서술 (한국어)]",
        "visualType": "[시각적 형태 (2D 또는 3D)]"
        }},
        {{
        "type": "예시 타입",
        "name": "예시 이름",
        "effect": "예시 효과 설명",
        "visualType": "2D"
        }}
    ]
    }}
    ```
    """
)
component_generation_chain = LLMChain(llm=llm_components, prompt=component_generation_prompt_template)

# -----------------------------------------------------------------------------
# 3. 구성요소 생성 함수
# -----------------------------------------------------------------------------
def generate_game_components_logic(plan_id: int) -> dict:
    """
    주어진 planId에 해당하는 컨셉, 세계관, 목표를 바탕으로 게임 구성요소를 생성합니다.
    """
    # 1. 데이터 조회
    data_entry = concept_and_goal_database.get(plan_id)
    if not data_entry:
        raise HTTPException(status_code=404, detail=f"Plan ID {plan_id}에 해당하는 컨셉/목표 데이터를 찾을 수 없습니다.")

    concept_data = data_entry.get("concept", {})
    world_data = data_entry.get("world", {})
    objective_data = data_entry.get("objective", {})

    # LLM 프롬프트에 전달할 정보 준비
    world_setting_str = json.dumps(world_data.get("setting", {}), ensure_ascii=False) if world_data.get("setting") else ""

    # 2. LLM Chain 호출
    try:
        response = component_generation_chain.invoke({
            "theme": concept_data.get("theme", ""),
            "playerCount": concept_data.get("playerCount", ""),
            "averageWeight": concept_data.get("averageWeight", 0.0),
            "ideaText": concept_data.get("ideaText", ""),
            "mechanics": concept_data.get("mechanics", ""),
            "storyline": concept_data.get("storyline", ""),
            "mainGoal": objective_data.get("mainGoal", ""),
            "winConditionType": objective_data.get("winConditionType", ""),
            "world_setting": world_setting_str,
            "world_tone": world_data.get("tone", "")
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 체인 실행 중 오류 발생: {e}")

    # 3. LLM 응답 파싱 및 후처리
    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            components_data = json.loads(json_str)
            # LLM이 직접 "components" 리스트를 생성하도록 유도했으므로, 그대로 반환
            final_response = {
                "componentId": np.random.randint(3000, 9999), # 3000~9999 사이의 랜덤 ID 생성
                "components": components_data["components"]
            }
            return final_response
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
# 4. FastAPI 엔드포인트 정의 (구성요소 생성)
# -----------------------------------------------------------------------------

# 요청 바디를 위한 Pydantic 모델 정의
class GenerateComponentsRequest(BaseModel):
    planId: int = Field(..., example=1012, description="구성요소를 생성할 기획안의 ID")

# 응답 바디를 위한 Pydantic 모델 정의 (사용자 요청 형식에 맞춤)
class ComponentItem(BaseModel):
    type: str
    name: str
    effect: str
    visualType: str # "2D" 또는 "3D"

class GenerateComponentsResponse(BaseModel):
    componentId: int
    components: List[ComponentItem]

# API 엔드포인트: 구성요소 생성
@app.post("/api/plans/generate-components", response_model=GenerateComponentsResponse, summary="컨셉/목표 기반 구성요소 생성")
async def generate_components_api(request: GenerateComponentsRequest):
    """
    주어진 `planId`에 해당하는 보드게임의 컨셉과 목표를 바탕으로 게임 구성요소를 생성합니다.
    """
    try:
        components_data = generate_game_components_logic(request.planId)
        return components_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류 발생: {e}")


# -----------------------------------------------------------------------------
# 5. (선택 사항) 기존 컨셉 생성 및 재생성 관련 코드 (간결함을 위해 생략 가능)
#    실제 프로젝트에서는 별도의 모듈로 분리하는 것이 좋습니다.
#    이전에 제공했던 컨셉/재생성 엔드포인트를 여기에 포함할 수 있습니다.
# -----------------------------------------------------------------------------
# 기존 컨셉/재생성 엔드포인트를 이 파일에 통합한다면 아래와 같이 추가할 수 있습니다.
# 예를 들어, concept_database를 planId를 키로 변경하거나,
# 각 엔드포인트에서 필요한 데이터만 조회하도록 로직을 조정해야 합니다.
# (본 예시에서는 구성요소 생성에만 집중하며 해당 코드는 생략합니다.)

# # 가상의 컨셉 데이터 저장소 (재생성 대상이 되는 원본 컨셉 포함)
# # 위 concept_and_goal_database와 통합하거나 별도 관리 필요
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
