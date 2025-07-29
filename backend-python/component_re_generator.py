import json
import re
import os
import numpy as np
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Literal

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# .env 파일에서 환경 변수 로드
# 이 파일을 실행하기 전에 프로젝트 루트 디렉터리에 .env 파일을 생성하고
# OPENAI_API_KEY=YOUR_API_KEY_HERE 와 같이 자신의 OpenAI API 키를 입력해주세요.
load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# FastAPI 애플리케이션 초기화
app = FastAPI(
    title="보드게임 구성요소 재생성 API",
    description="LLM을 활용하여 게임 구성요소를 피드백에 따라 재생성하는 API입니다.",
    version="1.0.0",
)

# CORS 설정 (모든 오리진 허용 - 개발용. 실제 서비스에서는 특정 도메인으로 제한 권장)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 가상의 컨셉, 세계관, 목표 데이터 저장소 (LLM에 컨텍스트 제공용)
# 실제 서비스에서는 DB나 파일에서 데이터를 조회하는 로직으로 대체됩니다.
concept_and_goal_database = {
    2001: { # planId 2001 (전략 게임)
        "concept": {
            "conceptId": 1001, "planId": 2001, "theme": "전략", "playerCount": "2~4명",
            "averageWeight": 3.0, "ideaText": "플레이어는 전략적인 지형을 활용해 상대를 견제하는 턴제 전투를 벌입니다. 각 라운드마다 새로운 카드를 드래프트하여 유닛을 소환하고, 영토를 확장하며 자원을 확보해야 합니다.",
            "mechanics": "지역 점령, 카드 드래프트, 핸드 매니지먼트, 자원 관리",
            "storyline": "고대 제국의 후예들이 전설의 유물을 차지하기 위해 맞붙는다. 사막의 모래폭풍, 숲의 맹수, 얼어붙은 산맥 등 다양한 지형이 전투에 영향을 미치며, 각 가문은 고유한 능력을 활용해 승리를 쟁취해야 한다."
        },
        "world": {
            "storyline": "오랜 전쟁으로 황폐해진 대륙에 고대 제국의 마지막 유물 '에테르 크리스탈'이 발견되었다.",
            "setting": { "era": "고대 제국 멸망 500년 후", "location": "파멸의 대륙 아르카디아", "factions": ["검은 독수리 가문"], "conflict": "에테르 크리스탈을 둘러싼 세력 간의 영토 및 자원 쟁탈전" },
            "tone": "전략적 경쟁 / 영토 확장"
        },
        "objective": {
            "mainGoal": "각 가문의 수장이 되어 에테르 크리스탈을 먼저 확보하고 대륙의 3개 주요 거점을 점령하십시오.",
            "winConditionType": "목표 달성형"
        }
    },
    1012: { # planId 1012 (시간 여행 판타지 게임)
        "concept": {
            "conceptId": 9999, "planId": 1012, "theme": "시간 여행 판타지", "playerCount": "2~4명",
            "averageWeight": 3.8, "ideaText": "시간을 조작하여 과거와 미래를 넘나들며 역사적 사건의 변칙을 바로잡는 게임입니다.",
            "mechanics": "시간 조작, 퍼즐 해결, 핸드 매니지먼트, 경로 만들기",
            "storyline": "시간의 강이 뒤틀리며 과거의 사건들이 예측 불가능하게 변하기 시작했습니다. '시간 수호자'들은 시간의 흐름을 원래대로 되돌리기 위해 시간 조각을 모으고, 역사적 변칙점을 찾아 수정해야 합니다."
        },
        "world": {
            "storyline": "우주 전체의 시간을 관장하는 신비로운 존재 '크로노스'가 잠들면서, 그의 힘이 약해져 시공간에 균열이 발생하기 시작했다.",
            "setting": { "era": "초월적인 시간", "location": "시간의 강, 과거와 미래의 주요 역사적 지점들", "factions": ["시간 수호자"], "conflict": "역사 복구 vs 시간의 파괴" },
            "tone": "신비로운 / 시간 기반 퍼즐 / 모험"
        },
        "objective": {
            "mainGoal": "시간의 강에 흩어진 5개의 '크로노스 코어'를 모두 수집하여 시간의 흐름을 안정화하고, 역사를 원래대로 되돌리십시오.",
            "winConditionType": "목표 달성형 / 퍼즐 해결형"
        }
    }
}

# 가상의 구성요소 데이터 저장소 (재생성 대상이 되는 원본 구성요소 포함)
# 실제 서비스에서는 DB에서 데이터를 조회하는 로직으로 대체됩니다.
components_database = {
    3543: { # componentId 3543 (planId 2001과 연관)
        "componentId": 3543,
        "components": [
            {
                "type": "토큰",
                "name": "지형 토큰",
                "effect": "지형 점령을 나타내는데 사용",
                "visualType": "3D"
            }
        ]
    },
    9999: { # componentId 9999 (planId 1012와 연관, generate_game_components_logic에서 생성될 수 있는 예시)
        "componentId": 9999,
        "components": [
            {
                "type": "보드",
                "name": "시간의 강 보드",
                "effect": "과거, 현재, 미래의 시간 흐름을 시각적으로 나타내며, 플레이어는 이 보드를 통해 시간 이동 경로를 계획합니다.",
                "visualType": "2D"
            },
            {
                "type": "토큰",
                "name": "크로노스 코어",
                "effect": "게임의 주요 목표 아이템으로, 5개를 모두 수집하면 승리 조건이 달성됩니다.",
                "visualType": "3D"
            },
            {
                "type": "카드",
                "name": "시간 조작 카드",
                "effect": "시간 이동, 특정 이벤트 발생, 적 조작 등 다양한 시간 조작 능력을 사용합니다.",
                "visualType": "2D"
            }
        ]
    }
}

# Pydantic 모델 정의
class ComponentItem(BaseModel):
    type: str
    name: str
    effect: str
    visualType: Literal["2D", "3D"]

class RegenerateComponentsRequest(BaseModel):
    componentId: int = Field(..., example=3543, description="재생성할 구성요소 묶음의 ID")
    feedback: str = Field(..., example="토큰타입의 지형토큰이 아닌 다른 토큰도 추가해주세요!", description="구성요소 재생성을 위한 피드백")

class RegenerateComponentsResponse(BaseModel):
    componentId: int
    components: List[ComponentItem]

# LLM 설정
llm_regenerate_components = ChatOpenAI(model_name="gpt-4o", temperature=0.7)

# 구성요소 재생성 프롬프트 템플릿
component_regeneration_prompt_template = PromptTemplate(
    input_variables=["current_components_json", "feedback", "theme", "playerCount", "averageWeight", "ideaText", "mechanics", "storyline", "mainGoal", "winConditionType", "world_setting", "world_tone"],
    template="""
    # Mission: 당신은 보드게임의 '리드 컴포넌트 전략가'로서, 기존에 설계된 게임 구성요소에 대한 피드백을 받아, 이를 반영하여 더욱 완벽한 구성요소 목록을 재생성하는 임무를 맡았습니다. 피드백의 의도를 정확히 파악하고, 기존 구성요소의 장점은 유지하되, 필요한 부분을 추가, 수정 또는 제거하여 최적의 목록을 도출해야 합니다.

    # Component Design Philosophy:
    1.  **피드백 반영 (Feedback Integration):** 주어진 피드백을 최우선으로 고려하여 구성요소 목록을 수정합니다.
    2.  **기능성 (Functionality):** 모든 구성요소는 반드시 게임의 핵심 메커니즘이나 목표 달성과 직접적으로 연결되어야 합니다.
    3.  **테마성 (Thematic Resonance):** 구성요소의 이름과 역할(effect)은 게임의 세계관과 스토리에 깊이 몰입하게 만드는 장치입니다.
    4.  **직관성 (Intuitive UX):** 플레이어가 구성요소를 보고 그 역할과 사용법을 쉽게 이해할 수 있어야 합니다. 'effect' 설명 시, 플레이어의 행동 관점에서 구체적으로 서술해주세요.
    5.  **기존 구성요소 유지/개선:** 기존에 존재하는 구성요소가 여전히 유효하다면 유지하고, 피드백에 따라 개선하거나 새로운 요소를 추가합니다. 불필요하다고 판단되면 제거할 수도 있습니다.

    # Input Data Analysis:
    ---
    **기존 보드게임 구성요소:**
    {current_components_json}

    **새로운 피드백:**
    {feedback}

    **보드게임 종합 정보 (참고용):**
    - 컨셉: {ideaText}
    - 메커니즘: {mechanics}
    - 주요 목표: {mainGoal}
    - 승리 조건: {winConditionType}
    - 세계관: {world_setting}, {storyline}
    - 전체적인 톤: {world_tone}
    ---

    # Final Output Instruction:
    이제, 위의 모든 지침과 철학, 그리고 피드백을 반영하여 아래 JSON 형식에 맞춰 최종 결과물만을 생성해주세요.
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
component_regeneration_chain = LLMChain(llm=llm_regenerate_components, prompt=component_regeneration_prompt_template)

# 구성요소 재생성 핵심 로직 함수
def regenerate_game_components_logic(component_id: int, feedback: str) -> dict:
    """
    주어진 componentId와 피드백을 바탕으로 게임 구성요소를 재생성합니다.
    """
    # 1. 기존 구성요소 데이터 조회
    existing_component_data = components_database.get(component_id)
    if not existing_component_data:
        raise HTTPException(status_code=404, detail=f"Component ID {component_id}에 해당하는 구성요소 데이터를 찾을 수 없습니다.")

    current_components_json_str = json.dumps(existing_component_data["components"], ensure_ascii=False, indent=2)

    # 이 componentId가 어떤 planId에 속하는지 찾아야 함 (LLM에게 컨텍스트 제공 위함)
    # 실제 DB 연동 시에는 componentId로 해당 planId와 연관된 컨셉/세계관/목표 데이터를 조회해야 합니다.
    # 여기서는 예시를 위해 components_database와 concept_and_goal_database를 순회하여 찾습니다.
    plan_id_for_component = None
    # 이 부분은 실제 서비스에서는 컴포넌트 데이터베이스에 planId를 직접 저장하여 O(1) 조회 가능하도록 개선하는 것이 좋습니다.
    # 현재는 예시를 위해 단순히 하드코딩된 매핑 또는 순회로 찾습니다.
    if component_id == 3543:
        plan_id_for_component = 2001
    elif component_id == 9999:
        plan_id_for_component = 1012
    # 추가적인 componentId-planId 매핑이 필요하면 여기에 추가

    if not plan_id_for_component:
        raise HTTPException(status_code=404, detail=f"Component ID {component_id}에 대한 기획안(planId) 정보를 찾을 수 없습니다. LLM에게 전달할 추가 정보가 부족합니다.")

    # 2. 관련 planId의 컨셉, 세계관, 목표 데이터 조회
    data_entry = concept_and_goal_database.get(plan_id_for_component)
    concept_data = data_entry.get("concept", {})
    world_data = data_entry.get("world", {})
    objective_data = data_entry.get("objective", {})
    world_setting_str = json.dumps(world_data.get("setting", {}), ensure_ascii=False) if world_data.get("setting") else ""

    # 3. LLM Chain 호출
    try:
        response = component_regeneration_chain.invoke({
            "current_components_json": current_components_json_str,
            "feedback": feedback,
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

    # 4. LLM 응답 파싱 및 후처리
    try:
        # LLM 응답에서 JSON 코드 블록 추출 (```json ... ``` 패턴)
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            components_data = json.loads(json_str) # JSON 문자열을 파이썬 딕셔너리로 변환
            
            final_response = {
                "componentId": component_id, # 기존 componentId 유지
                "components": components_data["components"]
            }
            # 실제 서비스에서는 components_database를 업데이트하는 로직이 여기에 추가됩니다.
            # 예: components_database[component_id]["components"] = components_data["components"]
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


# FastAPI 엔드포인트: 구성요소 재생성
@app.post("/api/plans/regenerate-components", response_model=RegenerateComponentsResponse, summary="기존 구성요소 재생성 (피드백 반영)")
async def regenerate_components_api(request: RegenerateComponentsRequest):
    """
    주어진 `componentId`의 기존 구성요소와 피드백을 바탕으로 새로운 구성요소 목록을 재생성합니다.
    """
    try:
        components_data = regenerate_game_components_logic(request.componentId, request.feedback)
        return components_data
    except HTTPException as e:
        raise e
    except Exception as e:
        # 예상치 못한 다른 모든 오류 처리
        raise HTTPException(status_code=500, detail=f"서버 오류 발생: {e}")
