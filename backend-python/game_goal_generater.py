import pandas as pd
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import datetime
import json
import re
import numpy as np
import os
from dotenv import load_dotenv # dotenv 모듈 추가

# FastAPI 관련 라이브러리
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 설정 (환경 변수에서 가져오기)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# -----------------------------------------------------------------------------
# 1. 가상의 컨셉 및 세계관 데이터 저장소
# -----------------------------------------------------------------------------
concept_and_world_database = {
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
        "world": { # 가상으로 추가된 세계관 데이터
            "storyline": "오랜 전쟁으로 황폐해진 대륙에 고대 제국의 마지막 유물 '에테르 크리스탈'이 발견되었다. 이 크리스탈을 차지하는 자가 대륙의 패권을 쥐게 될 것이다. 각 가문은 전설 속 유물을 찾아 전쟁을 시작한다.",
            "setting": {
                "era": "고대 제국 멸망 500년 후",
                "location": "파멸의 대륙 아르카디아",
                "factions": ["검은 독수리 가문", "황금 사자 가문", "하얀 늑대 가문"],
                "conflict": "에테르 크리스탈을 둘러싼 세력 간의 영토 및 자원 쟁탈전"
            },
            "tone": "전략적 경쟁 / 영토 확장"
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
        "world": { # 가상으로 추가된 세계관 데이터
            "storyline": "인류는 멸망의 위기에 처했고, 마지막 희망은 '크세논'이라 불리는 미지의 행성뿐이었다. 하지만 크세논은 겉보기와 달리 고대 문명의 잔해와 치명적인 외계 생명체, 그리고 알 수 없는 에너지장이 뒤덮인 곳이었다. 탐사팀은 생존과 함께 행성의 비밀을 파헤쳐야 한다.",
            "setting": {
                "era": "2242년",
                "location": "행성 크세논",
                "factions": ["지구 탐사대", "선구자 유물 수집가", "크세논 토착 생명체"],
                "conflict": "혹독한 환경에서의 생존 및 행성 크세논의 고대 비밀 해독"
            },
            "tone": "긴장감 있는 생존 / 미스터리 탐험"
        }
    },
    12: {
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
        "world": { # 가상으로 추가된 세계관 데이터
            "storyline": "인류의 마지막 희망을 싣고 떠난 우주선 '아크론'은 미지의 행성 '제노스-7' 상공에서 파괴되었다. 소수의 생존자들은 행성 표면에 불시착했지만, 제노스-7은 붉은 먼지 폭풍과 기이한 식물, 그리고 지저분한 '코랄'이라 불리는 외계 생명체들로 가득한 지옥이었다. 생존자들은 파편화된 비상 신호 장치를 재조립하여 구조 신호를 보내고, 그 전까지 행성의 위협으로부터 버텨내야 한다.",
            "setting": {
                "era": "2350년, 포스트-아포칼립스 우주",
                "location": "행성 제노스-7의 '붉은 황무지'",
                "factions": ["아크론 잔존 생존자", "행성 토착 코랄 종족", "미지의 고대 기계 지성체"],
                "conflict": "구조 신호 송신을 위한 자원 확보 및 외계 환경과 생명체로부터의 생존"
            },
            "tone": "절망적 생존 / 협력과 배신"
        }
    }
}

# -----------------------------------------------------------------------------
# 2. LLM 설정 및 프롬프트 정의
# -----------------------------------------------------------------------------

llm = ChatOpenAI(model_name="gpt-4o", temperature=0.7) # 게임 목표는 좀 더 명확해야 하므로 temperature를 낮춤

# 게임 목표 설계를 위한 프롬프트 템플릿 - 사용자 요청 형식에 맞춤
game_objective_prompt_template = PromptTemplate(
    input_variables=["theme", "playerCount", "averageWeight", "ideaText", "mechanics", "storyline", "world_setting", "world_tone"],
    template="""# Mission: 당신은 플레이어의 몰입도를 극대화하는 게임 목표를 설계하는 데 특화된 '리드 게임 디자이너'입니다. 당신의 임무는 주어진 컨셉과 세계관 정보를 깊이 있게 분석하여, 플레이어에게 강력한 동기를 부여하고 게임의 모든 메커니즘을 유기적으로 활용하게 만드는 핵심 게임 목표를 창조하는 것입니다.

# Core Principles of Objective Design:
1.  **서사적 연결 (Narrative-Driven):** 목표는 세계관의 핵심 갈등을 해결하는 행위여야 합니다. '왜 싸우는가?'에 대한 답을 목표가 제시해야 합니다. 예를 들어, '에테르 크리스탈'을 차지하기 위해 경쟁하는 세계관이라면, 목표는 '가장 많은 크리스탈 조각을 모으거나 중앙 제단을 활성화하는 것'이 될 수 있습니다.
2.  **메커니즘 활용 (Mechanics-Centric):** 설계된 목표는 주어진 메커니즘(예: 지역 점령, 덱 빌딩)을 자연스럽게 사용하도록 유도해야 합니다. 메커니즘이 목표 달성을 위한 '도구'가 되어야 합니다.
3.  **명확성과 긴장감 (Clarity & Tension):** 승리 조건은 명확해야 하지만, 게임이 끝날 때까지 승자를 예측하기 어렵게 만들어 긴장감을 유지해야 합니다. 단 하나의 길이 아닌, 여러 부가 목표를 통해 점수를 획득하는 방식이 좋은 예시입니다.

# Input Data Analysis:
---
**보드게임 컨셉 및 세계관 정보:**
-   테마: {theme}
-   플레이 인원수: {playerCount}
-   난이도: {averageWeight}
-   핵심 아이디어: {ideaText}
-   주요 메커니즘: {mechanics}
-   기존 스토리라인: {storyline}
-   세계관 설정: {world_setting}
-   세계관 분위기: {world_tone}
---

# Final Output Instruction:
이제, 위의 모든 지침과 원칙을 따라 아래 JSON 형식에 맞춰 최종 결과물만을 생성해주세요.
**JSON 코드 블록 외에 어떤 인사, 설명, 추가 텍스트도 절대 포함해서는 안 됩니다.**
모든 내용은 **풍부하고 자연스러운 한국어**로 작성되어야 합니다.

```json
{{
  "mainGoal": "[게임의 최종 승리 조건을 한 문장으로 명확하게 정의. 플레이어는 무엇을 달성하면 게임에서 승리하는가? (한국어)]",
  "subGoals": [
    "[주요 목표 달성을 돕거나, 점수를 얻을 수 있는 구체적인 보조 목표들. 플레이어에게 다양한 전략적 선택지를 제공해야 함. (한국어)]",
    "[또 다른 보조 목표 (필요 시 추가). (한국어)]"
  ],
  "winConditionType": "[승리 조건의 핵심 분류. (예: 점수 경쟁형, 목표 달성형, 마지막 생존형, 비밀 임무형)]",
  "designNote": "[이러한 게임 목표가 왜 이 게임에 최적인지에 대한 설계 의도. 어떻게 테마를 강화하고, 플레이어 간의 상호작용을 유도하는지 설명. (한국어)]"
}}
    ```
    """
)

game_objective_chain = LLMChain(llm=llm, prompt=game_objective_prompt_template)

# -----------------------------------------------------------------------------
# 3. 게임 목표 생성 함수 (FastAPI 통합을 위해 수정)
# -----------------------------------------------------------------------------

def generate_game_objective_logic(concept_id: int) -> dict:
    """
    주어진 conceptId에 해당하는 보드게임 컨셉과 세계관을 바탕으로 게임 목표를 생성합니다.
    """
    # 1. 컨셉 및 세계관 데이터 조회
    data_entry = concept_and_world_database.get(concept_id)
    if not data_entry:
        # FastAPI에서 HTTPException을 발생시켜 클라이언트에 404 에러를 반환
        raise HTTPException(status_code=404, detail=f"Concept ID {concept_id}에 해당하는 데이터를 찾을 수 없습니다.")

    concept_data = data_entry.get("concept", {})
    world_data = data_entry.get("world", {})

    # 세계관 설정 부분을 문자열로 변환하여 프롬프트에 전달 (중첩된 딕셔너리이므로 필요)
    world_setting_str = json.dumps(world_data.get("setting", {}), ensure_ascii=False) if world_data.get("setting") else ""

    # 2. LLM Chain 호출
    try:
        response = game_objective_chain.invoke({
            "theme": concept_data.get("theme", ""),
            "playerCount": concept_data.get("playerCount", ""),
            "averageWeight": concept_data.get("averageWeight", 0.0),
            "ideaText": concept_data.get("ideaText", ""),
            "mechanics": concept_data.get("mechanics", ""),
            "storyline": concept_data.get("storyline", ""), # 컨셉의 스토리라인 요약
            "world_setting": world_setting_str,            # 상세 세계관 설정 (JSON 문자열)
            "world_tone": world_data.get("tone", "")       # 세계관 분위기
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 체인 실행 중 오류 발생: {e}")

    # 3. LLM 응답 파싱 및 후처리
    try:
        # ```json ... ``` 패턴을 정규 표현식으로 정확히 찾아 파싱
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)

        if json_match:
            json_str = json_match.group(1)
            game_objective = json.loads(json_str)
        else:
            raise ValueError("LLM 응답에서 유효한 JSON 블록을 찾을 수 없습니다.")

        return game_objective
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
# 4. FastAPI 애플리케이션 설정
# -----------------------------------------------------------------------------

app = FastAPI(
    title="보드게임 게임 목표 생성 API",
    description="LLM을 사용하여 보드게임 컨셉 및 세계관을 바탕으로 게임 목표를 생성하는 API입니다.",
    version="1.0.0",
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처 허용. 실제 배포 시에는 특정 프론트엔드 주소만 허용하는 것이 좋습니다.
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# 요청 바디를 위한 Pydantic 모델 정의
class GameObjectiveRequest(BaseModel):
    conceptId: int = Field(..., example=12, description="게임 목표를 생성할 보드게임 컨셉의 ID")

# 응답 바디를 위한 Pydantic 모델 정의
class GameObjectiveResponse(BaseModel):
    mainGoal: str = Field(..., description="플레이어가 게임에서 궁극적으로 달성해야 할 주요 목표")
    subGoals: list[str] = Field(..., description="승리에 기여할 수 있는 보조 목표 목록")
    winConditionType: str = Field(..., description="승리 조건 유형 (예: 목표 달성형, 생존형, 점수 경쟁형 등)")
    designNote: str = Field(..., description="게임 목표 설계에 대한 간략한 디자이너 노트 또는 의도 설명")

# API 엔드포인트 정의
@app.post("/api/plans/generate-goal", response_model=GameObjectiveResponse, summary="게임 목표 생성")
async def generate_objective_api(request: GameObjectiveRequest):
    """
    주어진 `conceptId`에 해당하는 보드게임 컨셉과 세계관을 바탕으로 구체적인 게임 목표를 생성합니다.
    """
    try:
        game_objective = generate_game_objective_logic(request.conceptId)
        return game_objective
    except HTTPException as e:
        raise e # generate_game_objective_logic에서 발생한 HTTPException을 그대로 전달
    except Exception as e:
        # 예상치 못한 다른 모든 예외 처리
        raise HTTPException(status_code=500, detail=f"서버 오류 발생: {e}")
