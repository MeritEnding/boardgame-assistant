import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
import numpy as np
import datetime
import json
import re # 정규 표현식 모듈 추가
import os
from dotenv import load_dotenv # dotenv 모듈 추가

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 설정 (환경 변수에서 가져오기)
# 실제 배포 시에는 환경 변수를 사용하는 것이 보안상 안전합니다.
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# CORS 설정: 프론트엔드와 백엔드가 다른 포트에서 실행될 때 필요
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 오리진 허용. 실제 배포 시에는 특정 프론트엔드 주소만 허용하는 것이 좋습니다.
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# boardgame_detaildata_1-101.csv 파일 경로
# 로컬 환경에 맞게 경로를 수정해야 할 수도 있습니다.
# 예: './boardgame_detaildata_1-101.csv' 또는 절대 경로
csv_file_path = "./boardgame_detaildata_1-101.json"

# 데이터 로드 및 전처리 (FastAPI 시작 시 한 번만 실행)
# 데이터 로드 및 전처리 (FastAPI 시작 시 한 번만 실행)
try:
    df = pd.read_json(csv_file_path) # <-- read_json으로 변경
    print(f"JSON 파일 로드 완료: {csv_file_path}") # <-- 메시지 변경 (선택 사항)
except FileNotFoundError:
    print(f"Error: The file '{csv_file_path}' was not found.")
    print("Please make sure the JSON file is in the correct directory or provide the full path.") # <-- 메시지 변경 (선택 사항)
    exit() # 파일이 없으면 애플리케이션 시작을 중단
    
# 필요한 컬럼만 선택하고 컬럼명 변경 (사용자 요청에 맞춰)
df_processed = df[[
    '게임ID', '이름', '설명', '최소인원', '최대인원', '난이도', '카테고리', '메커니즘'
]].copy()

df_processed.rename(columns={
    '카테고리': '테마',
    '최소인원': 'min_players',
    '최대인원': 'max_players',
    '난이도': 'difficulty_weight',
    '메커니즘': 'mechanics_list'
}, inplace=True)

# 데이터 타입 변환 및 결측치 처리 (필요에 따라)
df_processed['min_players'] = pd.to_numeric(df_processed['min_players'], errors='coerce').fillna(1).astype(int)
df_processed['max_players'] = pd.to_numeric(df_processed['max_players'], errors='coerce').fillna(99).astype(int)
df_processed['difficulty_weight'] = pd.to_numeric(df_processed['difficulty_weight'], errors='coerce').fillna(2.0) # 평균 난이도 2.0으로 결측치 채움

# '테마'와 'mechanics_list' 컬럼의 NaN을 빈 문자열로 대체 (문자열 연산 시 오류 방지)
df_processed['테마'] = df_processed['테마'].fillna('')
df_processed['mechanics_list'] = df_processed['mechanics_list'].fillna('')

print("데이터 전처리 완료. 처음 5개 행:")
print(df_processed.head())

# 임베딩 모델 로드
embeddings = OpenAIEmbeddings()

# 각 행을 문서로 변환 (검색을 위해 관련 정보를 한 문자열로 합침)
documents = []
for index, row in df_processed.iterrows():
    content = (
        f"게임 이름: {row['이름']}\n"
        f"설명: {row['설명']}\n"
        f"테마: {row['테마']}\n"
        f"플레이 인원: {row['min_players']}~{row['max_players']}명\n"
        f"난이도: {row['difficulty_weight']:.2f}\n"
        f"메커니즘: {row['mechanics_list']}"
    )
    documents.append(content)

# FAISS 벡터 스토어 생성 및 로드
faiss_index_path = "faiss_boardgame_index"
try:
    # allow_dangerous_deserialization=True는 외부에서 직렬화된 데이터를 로드할 때 필요
    # 보안에 주의해야 하지만, 여기서는 직접 생성하는 파일이므로 허용합니다.
    vectorstore = FAISS.load_local(faiss_index_path, embeddings, allow_dangerous_deserialization=True)
    print("기존 FAISS 인덱스 로드 완료.")
except RuntimeError: # 파일이 없거나 로드 실패 시
    print("FAISS 인덱스가 없거나 로드에 실패했습니다. 새로 생성합니다.")
    vectorstore = FAISS.from_texts(documents, embeddings)
    vectorstore.save_local(faiss_index_path)
    print("새로운 FAISS 인덱스 생성 및 저장 완료.")

retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) # 상위 5개 결과 검색

# LLM 모델 로드
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7) # gpt-4o 또는 gpt-3.5-turbo 사용 가능

# 컨셉 생성을 위한 프롬프트 템플릿 - 한국어 지시 및 JSON 파싱 강화
prompt_template = PromptTemplate(
    input_variables=["theme", "playerCount", "averageWeight", "retrieved_games"],
    template="""# Mission: 당신은 세계적인 명성을 가진 보드게임 기획자이자, 독창적인 아이디어를 구체적인 컨셉으로 만드는 데 특화된 비저너리(Visionary)입니다. 당신의 임무는 사용자의 요청과 유사 게임 데이터를 깊이 분석하여, 세상에 없던 새로운 재미를 선사할 혁신적인 보드게임 컨셉을 창조하는 것입니다.

# Guiding Principles for a Successful Concept:
1. **독창성 (Originality):** 제시된 참고 데이터를 영감의 원천으로만 삼으세요. 아이디어나 메커니즘을 그대로 가져오지 말고, 완전히 새로운 경험을 제안해야 합니다. 여러 메커니즘을 창의적으로 융합하거나 기존에 없던 새로운 규칙을 고안하세요.
2. **일관성 (Coherence):** 게임의 테마, 스토리, 메커니즘이 유기적으로 연결되어야 합니다. 모든 요소가 하나의 목표를 향해 조화를 이루도록 설계해주세요. 왜 이 테마에 이 메커니즘이 어울리는지 명확히 드러나야 합니다.
3. **구체성 (Specificity):** 'ideaText', 'mechanics', 'storyline'은 누구나 게임의 그림을 그릴 수 있도록 구체적이고 생생하게 묘사해야 합니다. 추상적인 표현(예: "재미있는 상호작용") 대신 구체적인 액션(예: "상대방의 자원을 빼앗는 '약탈' 카드 사용")을 설명해주세요.
4. **언어 (Language):** 모든 핵심 설명('ideaText', 'mechanics', 'storyline')은 반드시 풍부하고 자연스러운 **한국어**로 작성되어야 합니다.

# Input Data Analysis:
### 1. User Request:
- 테마: {theme}
- 플레이 인원수: {playerCount}
- 난이도 (1.0~5.0): {averageWeight}

### 2. Reference Data for Inspiration:
(이 게임들은 아이디어를 얻기 위한 참고 자료일 뿐, 절대 복사해서는 안 됩니다.)
---
{retrieved_games}
---

# Final Output Instruction:
이제, 위의 모든 지침과 원칙을 따라 아래 JSON 형식에 맞춰 최종 결과물만을 생성해주세요.
**JSON 코드 블록 외에 어떤 인사, 설명, 추가 텍스트도 절대 포함해서는 안 됩니다.**

```json
{{
  "conceptId": [고유한 숫자],
  "planId": [고유한 숫자],
  "theme": "{theme}",
  "playerCount": "{playerCount}",
  "averageWeight": {averageWeight},
  "ideaText": "[새로운 보드게임의 핵심 플레이 경험과 승리 조건을 구체적으로 설명 (한국어)]",
  "mechanics": "[게임의 핵심 메커니즘들을 나열하고, 각 메커니즘이 테마와 어떻게 연결되는지 간략히 설명 (한국어)]",
  "storyline": "[플레이어들이 몰입할 수 있는 매력적인 배경 세계관과 그 속에서 플레이어의 역할을 설명 (한국어)]",
  "createdAt": "[현재 ISO 8601 형식 시간]"
}}
    ```
    """
)

# LLM Chain 설정
concept_generation_chain = LLMChain(llm=llm, prompt=prompt_template)

# 요청 바디를 위한 Pydantic 모델 정의
class BoardgameConceptRequest(BaseModel):
    theme: str
    playerCount: str
    averageWeight: float

# 응답 모델 (옵션: 명확한 API 문서화를 위해)
class BoardgameConceptResponse(BaseModel):
    conceptId: int
    planId: int
    theme: str
    playerCount: str
    averageWeight: float
    ideaText: str
    mechanics: str
    storyline: str
    createdAt: str

@app.post("/api/plans/generate-concept", response_model=BoardgameConceptResponse)
async def generate_boardgame_concept_api(user_input: BoardgameConceptRequest):
    theme = user_input.theme
    player_count_str = user_input.playerCount
    average_weight = user_input.averageWeight

    # 플레이 인원수 문자열 파싱 (예: "2~4명" -> min_players=2, max_players=4)
    # 현재는 RAG 검색 쿼리에만 사용되고 LLM 입력에는 문자열 그대로 전달됩니다.
    min_players_user, max_players_user = 1, 99 # 기본값
    if '~' in player_count_str:
        parts = player_count_str.replace('명', '').split('~')
        try:
            min_players_user = int(parts[0].strip())
            max_players_user = int(parts[1].strip())
        except ValueError:
            pass # 파싱 실패 시 기본값 사용
    else: # 단일 숫자일 경우 (예: "3명")
        try:
            min_players_user = int(player_count_str.replace('명', '').strip())
            max_players_user = min_players_user
        except ValueError:
            pass

    # RAG를 위한 검색 쿼리 생성
    search_query = (
        f"테마: {theme}, 플레이 인원: {player_count_str}, 난이도: {average_weight}. "
        f"이와 유사한 기존 보드게임들의 설명과 메커니즘을 찾아줘."
    )

    # 벡터 스토어에서 관련 문서 검색
    retrieved_docs = retriever.invoke(search_query)

    # 검색된 문서 내용을 하나의 문자열로 결합
    retrieved_games_info = "\n\n".join([doc.page_content for doc in retrieved_docs])

    # 검색된 데이터를 바탕으로 LLM 체인 실행
    try:
        response = concept_generation_chain.invoke({
            "theme": theme,
            "playerCount": player_count_str,
            "averageWeight": average_weight,
            "retrieved_games": retrieved_games_info
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 체인 실행 오류: {e}")

    # LLM 응답 파싱 및 추가 처리
    try:
        # LLM이 생성한 JSON 문자열을 정규 표현식으로 정확히 찾아 파싱
        # ```json ... ``` 패턴을 찾습니다.
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)

        if json_match:
            json_str = json_match.group(1)
            concept = json.loads(json_str)
        else:
            raise ValueError("LLM 응답에서 유효한 JSON 블록을 찾을 수 없습니다.")

        # conceptId, planId, createdAt 추가/업데이트 (LLM이 생성하지 않았을 경우 대비)
        # LLM에게 생성하라고 지시했으므로, 여기서 다시 덮어쓰거나 확인하는 로직이 필요할 수 있습니다.
        # 현재 코드에서는 LLM이 생성한 값을 사용하도록 프롬프트에 명시되어 있으므로,
        # LLM이 생성한 값을 그대로 사용하는 것이 더 자연스럽습니다.
        # 다만, 안전을 위해 랜덤 ID 생성 로직을 유지할 수도 있습니다.
        concept["conceptId"] = concept.get("conceptId", np.random.randint(1000, 9999))
        concept["planId"] = concept.get("planId", np.random.randint(2000, 9999))
        concept["createdAt"] = concept.get("createdAt", datetime.datetime.now().isoformat(timespec='seconds'))

        return concept
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"JSON 파싱 또는 데이터 처리 오류: {e}")
        print(f"LLM 응답 텍스트: {response['text']}")
        raise HTTPException(status_code=500, detail=f"LLM 응답을 처리하는 중 오류가 발생했습니다: {e}. 원본 응답: {response['text']}")
