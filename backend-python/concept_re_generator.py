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
# 1. 가상의 데이터 저장소 (모든 기획 데이터 통합)
#    실제 서비스에서는 DB에서 데이터를 조회하는 로직으로 대체됩니다.
# -----------------------------------------------------------------------------
# planId와 conceptId를 동시에 고려할 수 있도록 구조화
# 재생성 기능은 conceptId를 사용하며, planId는 참조용으로만 사용됩니다.
concept_database_for_regen = {
    1001: {
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
    1002: {
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
    12: { # 요청하신 conceptId 12의 예시 데이터
        "conceptId": 12,
        "planId": 13, # 요청에 따라 planId 13으로 변경
        "theme": "SF 생존/전략",
        "playerCount": "2~4명",
        "averageWeight": 3.5,
        "ideaText": "알 수 없는 외계 행성에 불시착한 생존자들이 제한된 자원을 활용하여 기지를 건설하고, 위험한 환경과 외계 생명체로부터 자신을 방어하며 탈출을 시도하는 협력 및 경쟁 게임입니다. 플레이어는 서로 협력하며 자원을 공유할 수도 있고, 배신하여 다른 팀의 자원을 빼앗을 수도 있습니다.",
        "mechanics": "자원 관리, 기지 건설, 타워 디펜스, 비대칭 능력, 협력/경쟁",
        "storyline": "지구의 자원 고갈로 인해 새로운 정착지를 찾아 우주선을 타고 떠난 인류. 예상치 못한 소행성 충돌로 미지의 행성에 불시착하게 된다. 이 행성은 아름답지만 치명적인 환경과 지능적인 외계 생명체가 서식하고 있었는데...",
        "createdAt": "2025-07-25T10:00:00"
    }
}

# 기획안 ID에 따른 상세 정보 (컨셉, 세계관, 목표 등)
# 이 데이터는 게임 목표, 구성요소, 규칙 생성에 사용됩니다.
# conceptId 12가 planId 13에 연결된 것으로 가정하고 데이터를 추가합니다.
concept_world_objective_database = {
    1001: {
        "concept": concept_database_for_regen[1001],
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
        "concept": concept_database_for_regen[1002],
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
    12: { # conceptId 12가 planId 13에 연결된 상세 데이터
        "concept": concept_database_for_regen[12],
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

# planId 기반 데이터베이스 (구성요소 생성에 사용)
# 이 예시에서는 concept_world_objective_database의 데이터를 planId로 접근할 수 있도록 매핑
plan_data_for_components = {
    item["concept"]["planId"]: item for item in concept_world_objective_database.values()
}
# 요청하신 planId 13에 대한 데이터 추가 (conceptId 12의 데이터와 동일)
if 12 in concept_world_objective_database:
    plan_data_for_components[concept_database_for_regen[12]["planId"]] = concept_world_objective_database[12]


# -----------------------------------------------------------------------------
# 2. LLM 설정 및 프롬프트 정의 (컨셉 재생성)
# -----------------------------------------------------------------------------

llm_regenerate = ChatOpenAI(model_name="gpt-4o", temperature=0.9) # 컨셉 재생성은 창의성이 중요하므로 temperature 높임

regenerate_concept_prompt_template = PromptTemplate(
    input_variables=["original_concept_json", "feedback", "plan_id"],
    template="""
    # Mission: 당신은 사용자의 피드백을 바탕으로 기존 게임 컨셉을 한 단계 발전시키는 '리드 컨셉 아티스트'이자 '게임 닥터'입니다. 당신의 임무는 주어진 원본 컨셉과 사용자 피드백을 깊이 있게 분석하고, 피드백의 핵심 의도를 파악하여 컨셉을 창의적으로 '재생성'하는 것입니다.

    # Regeneration Process:
    1.  **피드백 분석 (Analyze Feedback):** 사용자의 피드백이 무엇을 의미하는지 깊이 파악합니다. 예를 들어, '좀 더 캐주얼하게'라는 피드백은 '낮은 난이도', '짧은 플레이 타임', '더 많은 소셜 인터랙션' 등을 의미할 수 있습니다.
    2.  **수정 전략 결정 (Decide on a Revision Strategy):** 피드백을 반영하기 위한 최적의 전략을 선택합니다.
        -   **부분 수정 (Partial Tweak):** 원본의 큰 틀은 유지하되, 테마의 톤앤매너나 일부 메커니즘을 수정하여 피드백을 반영합니다.
        -   **전면 개편 (Complete Overhaul):** 피드백을 반영하기 위해 원본의 테마와 핵심 메커니즘을 완전히 새롭게 재구성합니다.
    3.  **컨셉 생성 (Generate Concept):** 결정된 전략에 따라, 모든 항목이 유기적으로 연결된 새로운 컨셉을 완성합니다. 모든 결과물은 **풍부하고 매력적인 한국어**로 작성해야 합니다.

    # Input Data:
    ---
    ### 1. Original Game Concept:
    ```json
    {original_concept_json}
    ```

    **사용자 피드백:**
    {feedback}

    **기존 기획안 ID (재생성된 컨셉에 동일하게 적용):**
    {plan_id}
    ---

    당신은 다음 JSON 형식으로만 응답해야 합니다. **다른 어떤 설명이나 추가적인 텍스트도 포함하지 마세요.**
    모든 내용은 **한국어**로 작성되어야 합니다.

    ```json
    {{
      "conceptId": [이전 ID와 겹치지 않는 새로운 고유 정수 ID. 임의의 4자리 숫자를 추천합니다.],
      "planId": {plan_id},
      "theme": "[피드백을 반영하여 수정되거나 완전히 새로워진 테마 (한국어)]",
      "playerCount": "[새 컨셉에 맞는 플레이어 수 (예: '2~4명', '1명', '3~6명')]",
      "averageWeight": [피드백에 따라 조절된 난이도. '캐주얼' 피드백이라면 낮추고, '더 전략적'이라면 높이세요. (1.0~5.0 사이 실수)],
      "ideaText": "[피드백이 반영된 새로운 핵심 플레이 경험을 구체적으로 설명 (한국어)]",
      "mechanics": "[새 컨셉의 핵심 메커니즘 목록. 피드백에 따라 기존 메커니즘을 수정, 삭제 또는 추가하세요. (콤마로 구분, 한국어)]",
      "storyline": "[새로운 테마와 분위기에 맞는 매력적인 스토리라인 (한국어)]",
      "createdAt": "[이 필드는 LLM이 채우지 않습니다. 비워두거나 현재 값을 유지하세요.]"
    }}
    ```
    """
)
regenerate_concept_chain = LLMChain(llm=llm_regenerate, prompt=regenerate_concept_prompt_template)

# -----------------------------------------------------------------------------
# 3. 컨셉 재생성 함수
# -----------------------------------------------------------------------------
def regenerate_board_game_concept_logic(request_data: dict) -> dict:
    concept_id_to_regenerate = request_data.get("conceptId")
    feedback = request_data.get("feedback", "")
    plan_id = request_data.get("planId")

    original_concept_data = concept_database_for_regen.get(concept_id_to_regenerate)
    if not original_concept_data:
        raise HTTPException(status_code=404, detail=f"Concept ID {concept_id_to_regenerate}에 해당하는 원본 데이터를 찾을 수 없습니다.")

    # 원본 데이터의 planId와 요청의 planId가 다르면 오류 (또는 경고)
    if original_concept_data.get("planId") != plan_id:
        print(f"경고: 요청된 planId ({plan_id})가 원본 컨셉의 planId ({original_concept_data.get('planId')})와 다릅니다. 원본 planId를 사용합니다.")
        plan_id = original_concept_data.get("planId")


    original_concept_json_str = json.dumps(original_concept_data, indent=2, ensure_ascii=False)

    try:
        response = regenerate_concept_chain.invoke({
            "original_concept_json": original_concept_json_str,
            "feedback": feedback,
            "plan_id": plan_id
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 체인 실행 중 오류 발생: {e}")

    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            regenerated_concept = json.loads(json_str)

            regenerated_concept["createdAt"] = datetime.datetime.now().isoformat(timespec='seconds')

            new_concept_id = regenerated_concept.get("conceptId")
            if new_concept_id:
                if isinstance(new_concept_id, int) and new_concept_id not in concept_database_for_regen:
                    concept_database_for_regen[new_concept_id] = regenerated_concept
                    print(f"새로운 컨셉 (ID: {new_concept_id})이 데이터베이스에 추가되었습니다.")
                else:
                    max_id = max(concept_database_for_regen.keys()) if concept_database_for_regen else 0
                    new_unique_id = max(max_id + 1, 1000)
                    # 현재 시간 KST (서울 기준)로 변경
                    kst_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
                    regenerated_concept["conceptId"] = new_unique_id
                    regenerated_concept["createdAt"] = kst_now.isoformat(timespec='seconds')
                    concept_database_for_regen[new_unique_id] = regenerated_concept
                    print(f"경고: LLM이 유효하지 않거나 중복된 conceptId ({new_concept_id})를 생성했습니다. 새로운 ID ({new_unique_id})로 할당합니다.")
            else:
                max_id = max(concept_database_for_regen.keys()) if concept_database_for_regen else 0
                new_unique_id = max(max_id + 1, 1000)
                kst_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
                regenerated_concept["conceptId"] = new_unique_id
                regenerated_concept["createdAt"] = kst_now.isoformat(timespec='seconds')
                concept_database_for_regen[new_unique_id] = regenerated_concept
                print(f"경고: LLM이 conceptId를 생성하지 못했습니다. 새로운 ID ({new_unique_id})로 할당합니다.")

            return regenerated_concept
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
# 4. FastAPI 엔드포인트 정의 (컨셉 재생성)
# -----------------------------------------------------------------------------

# 요청 바디를 위한 Pydantic 모델 정의
class RegenerateConceptRequest(BaseModel):
    conceptId: int = Field(..., example=12, description="재생성할 원본 컨셉의 ID")
    planId: int = Field(..., example=13, description="재생성된 컨셉에 유지될 기획안 ID")
    feedback: str = Field(..., example="좀 더 캐주얼한 분위기였으면 좋겠어요.", description="컨셉 재생성을 위한 사용자 피드백")

# 응답 바디를 위한 Pydantic 모델 정의
class RegeneratedConceptResponse(BaseModel):
    conceptId: int
    planId: int
    theme: str
    playerCount: str
    averageWeight: float
    ideaText: str
    mechanics: str
    storyline: str
    createdAt: str


# API 엔드포인트: 컨셉 재생성
@app.post("/api/plans/regenerate-concept", response_model=RegeneratedConceptResponse, summary="기존 보드게임 컨셉 재생성 (피드백 반영)")
async def regenerate_concept_api_endpoint(request: RegenerateConceptRequest):
    """
    주어진 `conceptId`와 `feedback`을 바탕으로 기존 보드게임 컨셉을 재생성합니다.
    `planId`는 원본 컨셉의 `planId`를 유지하며, 데이터베이스에 새로운 컨셉 ID로 저장됩니다.
    """
    try:
        regenerated_concept = regenerate_board_game_concept_logic(request.dict())
        return regenerated_concept
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류 발생: {e}")


# -----------------------------------------------------------------------------
# 5. (선택 사항) 기존 컨셉 생성, 게임 목표 생성, 구성요소 생성 관련 코드
#    모든 기능을 하나의 FastAPI 앱으로 구성한다면 아래의 코드들도 함께 유지해야 합니다.
#    간결함을 위해 본 예시에서는 관련 데이터베이스, LLM 체인, 함수, 엔드포인트 코드를 주석 처리합니다.
#    실제 프로젝트에서는 별도의 모듈로 분리하거나, 이들을 적절히 통합해야 합니다.
# -----------------------------------------------------------------------------

# # -- 컨셉 생성 관련 --
# # boardgame_detaildata_1-101.json 파일 경로
# # csv_file_path = "./boardgame_detaildata_1-101.json"
# # # 데이터 로드 및 전처리 (FastAPI 시작 시 한 번만 실행)
# # try:
# #     df = pd.read_json(csv_file_path)
# #     print(f"JSON 파일 로드 완료: {csv_file_path}")
# # except FileNotFoundError:
# #     print(f"Error: The file '{csv_file_path}' was not found.")
# #     print("Please make sure the JSON file is in the correct directory or provide the full path.")
# #     df = pd.DataFrame()
# # except Exception as e:
# #     print(f"Error loading or processing JSON file: {e}")
# #     df = pd.DataFrame()
# #
# # df_processed = pd.DataFrame()
# # if not df.empty:
# #     df_processed = df[['게임ID', '이름', '설명', '최소인원', '최대인원', '난이도', '카테고리', '메커니즘']].copy()
# #     df_processed.rename(columns={'카테고리': '테마', '최소인원': 'min_players', '최대인원': 'max_players', '난이도': 'difficulty_weight', '메커니즘': 'mechanics_list'}, inplace=True)
# #     df_processed['min_players'] = pd.to_numeric(df_processed['min_players'], errors='coerce').fillna(1).astype(int)
# #     df_processed['max_players'] = pd.to_numeric(df_processed['max_players'], errors='coerce').fillna(99).astype(int)
# #     df_processed['difficulty_weight'] = pd.to_numeric(df_processed['difficulty_weight'], errors='coerce').fillna(2.0)
# #     df_processed['테마'] = df_processed['테마'].fillna('')
# #     df_processed['mechanics_list'] = df_processed['mechanics_list'].fillna('')
# #
# # from langchain_community.vectorstores import FAISS
# # from langchain_openai import OpenAIEmbeddings
# # embeddings = OpenAIEmbeddings()
# # faiss_index_path = "faiss_boardgame_index"
# # vectorstore = None
# # if not df.empty:
# #     documents = []
# #     for index, row in df_processed.iterrows():
# #         content = (f"게임 이름: {row['이름']}\n" f"설명: {row['설명']}\n" f"테마: {row['테마']}\n" f"플레이 인원: {row['min_players']}~{row['max_players']}명\n" f"난이도: {row['difficulty_weight']:.2f}\n" f"메커니즘: {row['mechanics_list']}")
# #         documents.append(content)
# #     try:
# #         vectorstore = FAISS.load_local(faiss_index_path, embeddings, allow_dangerous_deserialization=True)
# #         print("기존 FAISS 인덱스 로드 완료.")
# #     except RuntimeError:
# #         print("FAISS 인덱스가 없거나 로드에 실패했습니다. 새로 생성합니다.")
# #         vectorstore = FAISS.from_texts(documents, embeddings)
# #         vectorstore.save_local(faiss_index_path)
# #         print("새로운 FAISS 인덱스 생성 및 저장 완료.")
# # retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) if vectorstore else None
# #
# # llm_generate = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
# # generate_concept_prompt_template = PromptTemplate(
# #     input_variables=["theme", "playerCount", "averageWeight", "retrieved_games"],
# #     template="""당신은 보드게임 컨셉 전문가입니다. ... """
# # )
# # concept_generation_chain = LLMChain(llm=llm_generate, prompt=generate_concept_prompt_template)
# #
# # class BoardgameConceptRequest(BaseModel):
# #     theme: str = Field(..., example="중세 판타지")
# #     playerCount: str = Field(..., example="2~4명")
# #     averageWeight: float = Field(..., example=2.5, ge=1.0, le=5.0)
# #
# # class BoardgameConceptResponse(BaseModel):
# #     conceptId: int
# #     planId: int
# #     theme: str
# #     playerCount: str
# #     averageWeight: float
# #     ideaText: str
# #     mechanics: str
# #     storyline: str
# #     createdAt: str
# #
# # @app.post("/generate-concept", response_model=BoardgameConceptResponse, summary="새로운 보드게임 컨셉 생성")
# # async def generate_boardgame_concept_api(user_input: BoardgameConceptRequest):
# #     # ... 컨셉 생성 로직
# #     pass
#
# # -- 게임 목표 생성 관련 --
# # llm_objective = ChatOpenAI(model_name="gpt-4o", temperature=0.7)
# # game_objective_prompt_template = PromptTemplate(
# #     input_variables=["theme", "playerCount", "averageWeight", "ideaText", "mechanics", "storyline", "world_setting", "world_tone"],
# #     template="""당신은 보드게임 디자이너입니다. ... """
# # )
# # game_objective_chain = LLMChain(llm=llm_objective, prompt=game_objective_prompt_template)
# #
# # def generate_game_objective_logic(concept_id: int) -> dict:
# #     # ... 게임 목표 생성 로직 (concept_world_objective_database 사용)
# #     pass
# #
# # class GameObjectiveRequest(BaseModel):
# #     conceptId: int = Field(..., example=12)
# #
# # class GameObjectiveResponse(BaseModel):
# #     mainGoal: str
# #     subGoals: List[str]
# #     winConditionType: str
# #     designNote: str
# #
# # @app.post("/generate-objective", response_model=GameObjectiveResponse, summary="게임 목표 생성")
# # async def generate_objective_api(request: GameObjectiveRequest):
# #     # ... 게임 목표 생성 로직
# #     pass
#
# # -- 구성요소 생성 관련 --
# # llm_components = ChatOpenAI(model_name="gpt-4o", temperature=0.7)
# # component_generation_prompt_template = PromptTemplate(
# #     input_variables=["theme", "playerCount", "averageWeight", "ideaText", "mechanics", "storyline", "mainGoal", "winConditionType", "world_setting", "world_tone"],
# #     template="""당신은 보드게임의 구성요소(컴포넌트) 디자이너입니다. ... """
# # )
# # component_generation_chain = LLMChain(llm=llm_components, prompt=component_generation_prompt_template)
# #
# # def generate_game_components_logic(plan_id: int) -> dict:
# #     # ... 구성요소 생성 로직 (plan_data_for_components 사용)
# #     pass
# #
# # class ComponentItem(BaseModel):
# #     type: str
# #     name: str
# #     effect: str
# #     visualType: str
# #
# # class GenerateComponentsResponse(BaseModel):
# #     components: List[ComponentItem]
# #
# # class GenerateComponentsRequest(BaseModel):
# #     planId: int = Field(..., example=1012)
# #
# # @app.post("/generate-components", response_model=GenerateComponentsResponse, summary="컨셉/목표 기반 구성요소 생성")
# # async def generate_components_api(request: GenerateComponentsRequest):
# #     # ... 구성요소 생성 로직
# #     pass
#
# # -- 게임 규칙 생성 관련 --
# # llm_rules = ChatOpenAI(model_name="gpt-4o", temperature=0.6)
# # game_rules_prompt_template = PromptTemplate(
# #     input_variables=["theme", "playerCount", "averageWeight", "ideaText", "mechanics", "storyline", "world_setting", "world_tone", "mainGoal", "subGoals", "winConditionType", "objective_designNote"],
# #     template="""당신은 보드게임 규칙 전문가입니다. ... """
# # )
# # game_rules_chain = LLMChain(llm=llm_rules, prompt=game_rules_prompt_template)
# #
# # def generate_game_rules_logic(concept_id: int) -> dict:
# #     # ... 게임 규칙 생성 로직 (concept_world_objective_database 사용)
# #     pass
# #
# # class GenerateRulesRequest(BaseModel):
# #     conceptId: int = Field(..., example=12)
# #
# # class GenerateRulesResponse(BaseModel):
# #     ruleId: int
# #     turnStructure: str
# #     actionRules: List[str]
# #     victoryCondition: str
# #     penaltyRules: List[str]
# #     designNote: str
# #
# # @app.post("/generate-rules", response_model=GenerateRulesResponse, summary="컨셉/목표 기반 게임 규칙 생성")
# # async def generate_rules_api(request: GenerateRulesRequest):
# #     # ... 게임 규칙 생성 로직
# #     pass
