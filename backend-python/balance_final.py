import os
import re
import json
import random
from typing import List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 환경 변수에서 OpenAI API 키를 설정합니다.
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

# FastAPI 애플리케이션을 초기화합니다.
app = FastAPI(
    title="간단한 게임 규칙 시뮬레이션 및 밸런스 분석 API",
    description="주어진 규칙 ID와 플레이어 정보로 가상 게임 플레이 로그를 생성하고, LLM 기반 게임 밸런스 피드백을 제공합니다.",
    version="1.0.0",
)

# CORS 설정을 추가합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# 1. 가상의 데이터 저장소 (게임 규칙 데이터베이스)
# -----------------------------------------------------------------------------
game_rules_database = {
    101: {
        "ruleId": 101,
        "gameName": "제노스-7 생존기",
        "turnStructure": "1. 자원 수집 → 2. 기지 건설 또는 탐색 → 3. 외계 생명체 이벤트 → 4. 턴 종료",
        "actionRules": [
            "자원 수집: 주변 타일에서 '에너지' 또는 '부품' 자원을 1개 획득합니다.",
            "기지 건설: '부품' 3개를 소모하여 방어 포탑을 건설합니다. 포탑은 외계 생명체 이벤트 시 방어력을 높여줍니다.",
            "탐색: '에너지' 1개를 소모하여 새로운 지역 타일을 공개하고, 낮은 확률로 '유물 부품'을 발견합니다.",
            "협력: 같은 칸에 있는 다른 플레이어와 자원을 교환할 수 있습니다."
        ],
        "victoryCondition": "팀 전체가 '유물 부품' 3개를 모아 비상 신호 장치를 수리하면 즉시 승리합니다.",
        "penaltyRules": [
            "외계 생명체 이벤트에서 방어에 실패하면 자원 1개를 잃습니다.",
            "특정 지역 타일은 위험 구역으로, 진입 시 '에너지'를 1개 소모합니다."
        ]
    }
}

# -----------------------------------------------------------------------------
# 2. LLM 설정 및 프롬프트 정의
# -----------------------------------------------------------------------------
llm_simulator = ChatOpenAI(model_name="gpt-4o", temperature=0.9)
llm_analyzer = ChatOpenAI(model_name="gpt-4o", temperature=0.5) # 밸런스 분석은 좀 더 보수적인 temperature

# 게임 시뮬레이션 프롬프트 템플릿
enhanced_simulation_prompt_template = PromptTemplate(
    input_variables=["game_rules_text", "player_names", "max_turns", "penalty_info"],
    template="""
# SYSTEM DIRECTIVE: AI Game Master (GM) Simulation Protocol

<SYSTEM_ROLE>
당신은 최고의 보드게임 AI 게임 마스터(GM)입니다. 당신의 임무는 주어진 게임 규칙과 플레이어 정보를 바탕으로, 논리적으로 일관되고 흥미로운 가상 플레이 시뮬레이션 로그를 생성하는 것입니다. 단순한 사건 나열이 아닌, 각 플레이어의 전략적 고민과 선택이 드러나는 한 편의 완성도 높은 플레이 다이어리를 작성해야 합니다.

* **플레이어 페르소나 부여:** 각 플레이어({player_names})에게 '신중한 전략가', '과감한 탐험가', '효율적인 기술자' 등 어울리는 페르소나를 마음속으로 부여하고, 그 페르소나에 입각하여 행동을 결정하게 하세요.
* **전략적 사고 시뮬레이션:** 각 턴마다 플레이어가 처한 상황(자원, 승리 조건까지의 거리 등)을 분석하고, 자신의 페르소나와 게임 규칙에 따라 어떤 선택이 가장 합리적일지 시뮬레이션해야 합니다.
</SYSTEM_ROLE>

<GAME_CONTEXT>
### 1. Game Rules:
{game_rules_text}

### 2. Players:
{player_names}

### 3. Session Conditions:
- Maximum Turns: {max_turns}
- Penalty Rules Enabled: {penalty_info}
</GAME_CONTEXT>

<CORE_TASK>
다음 지침에 따라 시뮬레이션을 단계별로 수행하고, 그 결과를 '내러티브 로그'와 '최종 요약 JSON' 형식으로 출력하세요.

**Task 1: Turn-by-Turn Narrative Log Generation**
1.  **턴 시작:** 현재 턴 번호를 명시하며 턴을 시작합니다. (예: **[ 1턴 ]**)
2.  **상황 분석:** 해당 턴 시작 시점의 게임 상황을 간략하게 요약합니다. (예: 현재 팀의 유물 부품은 1개, B는 에너지가 부족한 상태...)
3.  **플레이어 행동 서술:** 각 플레이어가 자신의 페르소나와 전략에 따라 어떤 고민 끝에 행동을 선택했는지, 그리고 그 행동의 결과가 무엇인지 구체적으로 서술합니다.
    * (예시) '공학자 B'는 외계 생명체의 위협이 임박했다고 판단, 안전하게 기지를 강화하기 위해 '부품' 3개를 소모하여 방어 포탑을 건설했습니다. 포탑이 완성되자 기지의 방어력이 눈에 띄게 증가했습니다.
4.  **턴 종료:** 모든 플레이어의 행동이 끝나면 턴을 종료하고, 다음 턴으로 넘어갑니다. 승리 조건이 충족되거나 최대 턴에 도달하면 시뮬레이션을 즉시 종료합니다.

**Task 2: Final Summary Generation**
1.  **게임 종료 선언:** 시뮬레이션이 종료되면, "게임 종료!"를 선언하고 승리/패배 조건, 최종 승자, 그리고 그 이유를 명확하게 설명합니다.
2.  **최종 요약 JSON 생성:** **내러티브 로그 작성이 모두 끝난 후, 출력의 맨 마지막 부분에** 다음 스키마를 엄격히 따르는 JSON 객체를 ` ```json ... ``` ` 코드 블록 안에 생성해야 합니다. **이 JSON 블록 앞뒤로 어떠한 추가 설명이나 텍스트도 절대 포함해서는 안 됩니다.**
</CORE_TASK>

<OUTPUT_FORMAT_SPECIFICATION>
### 내러티브 로그 예시:
**[ 1턴 ]**
탐험가 A와 공학자 B는 제노스-7의 황량한 땅에 불시착했습니다. 생존을 위해 신속한 판단이 필요한 상황.
- 탐험가 A: 위험을 감수하더라도 빠르게 유물을 찾는 것이 중요하다고 판단, '에너지' 1개를 소모하여 미지의 동쪽 지역을 탐색했다. 다행히 새로운 '에너지' 자원을 발견했다!
- 공학자 B: 장기적인 방어 계획을 위해 '부품'을 모으기로 결정. 주변 폐허에서 '부품' 1개를 수집했다.

**[ 2턴 ]**... (시뮬레이션 진행) ...

**게임 종료!**
승자: 탐험가 A, 공학자 B (팀 승리)
두 플레이어는 8턴 만에 힘을 합쳐 유물 부품 3개를 모두 모아 신호 장치를 수리하는 데 성공했습니다. A의 과감한 탐색과 B의 안정적인 기지 운영이 만들어낸 완벽한 승리입니다.

### 최종 요약 JSON (Strict Schema):
```json
{{
  "winner": "탐험가 A, 공학자 B",
  "totalTurns": 8,
  "victoryCondition": "팀 전체가 '유물 부품' 3개를 모아 비상 신호 장치 수리 완료",
  "durationMinutes": 42,
  "score": {{
    "탐험가 A": 25,
    "공학자 B": 20
  }},
  "turns": [
    {{
      "turn": 1,
      "actions": [
        {{
          "player": "탐험가 A",
          "action": "탐색",
          "details": "'에너지' 1개 소모, 새로운 '에너지' 자원 발견",
          "rationale": "빠른 유물 부품 확보를 위한 선제적 탐색"
        }},
        {{
          "player": "공학자 B",
          "action": "자원 수집",
          "details": "'부품' 1개 획득",
          "rationale": "미래의 기지 건설을 위한 자원 축적"
        }}
      ]
    }}
  ]
}}
"""
)
enhanced_simulation_chain = LLMChain(llm=llm_simulator, prompt=enhanced_simulation_prompt_template)


# 게임 밸런스 분석 프롬프트 템플릿 (새로 추가)
game_balance_prompt_template = PromptTemplate(
    input_variables=["game_rules_text"],
    template="""
# SYSTEM DIRECTIVE: AI Game Balance Analyst

<SYSTEM_ROLE>
당신은 주어진 게임 규칙을 분석하여 잠재적인 밸런스 문제점과 그에 대한 개선 방안을 전문적으로 제시하는 'AI 게임 밸런스 분석가'입니다. 게임의 승리 조건, 자원 획득/소모, 플레이어 액션, 페널티 규칙 등을 종합적으로 고려하여 공정하고 재미있는 플레이 경험을 저해할 수 있는 요소를 식별하고, 구체적인 수정 제안을 해주세요.

당신의 분석은 다음과 같은 JSON 형식으로만 이루어져야 합니다.
</SYSTEM_ROLE>

<GAME_RULES_FOR_ANALYSIS>
### 1. Game Rules:
{game_rules_text}
</GAME_RULES_FOR_ANALYSIS>

<CORE_TASK>
위 게임 규칙을 철저히 분석하여 다음 스키마에 따라 JSON 객체를 생성하세요.

* `simulationSummary`: 이 게임의 가상 플레이 테스트에서 예상되는 전반적인 특징 (예: "이 게임은 팀 플레이가 중요하며, 자원 관리가 핵심적인 요소가 될 것으로 예상됩니다.")
* `issuesDetected`: 규칙에서 발견되는 잠재적인 밸런스 문제점 목록 (예: "특정 액션의 효율이 지나치게 높음", "후반으로 갈수록 자원 불균형 심화 예상")
* `recommendations`: 발견된 문제점에 대한 구체적인 개선 방안 목록 (예: "'자원 수집' 시 획득량 조절", "특정 플레이어 역할에 추가적인 핸디캡 부여")
* `balanceScore`: 1.0 (매우 불균형) ~ 10.0 (완벽한 균형) 사이의 밸런스 평점. 당신의 분석을 바탕으로 합리적인 점수를 부여하세요.

</CORE_TASK>

<OUTPUT_FORMAT_SPECIFICATION>
```json
{{
  "balanceAnalysis": {{
    "simulationSummary": "총 20회 플레이 테스트 결과, 평균 게임 시간은 38분이며, 평균 승리 점수는 12점이었습니다.",
    "issuesDetected": [
      "일부 플레이어가 첫 턴부터 유리한 자원을 독점할 가능성이 있음",
      "‘탐색’ 액션의 성공 확률이 너무 낮아 동기 부여가 부족할 수 있음",
      "외계 생명체 이벤트 실패 시 페널티가 미미하여 위기감이 적음"
    ],
    "recommendations": [
      "초기 자원 배분을 시작 카드 드래프트 방식으로 변경하여 불균형 완화",
      "‘탐색’ 성공 확률을 미세하게 상향 조정하고, 실패 시에도 소량의 보상 제공",
      "외계 생명체 이벤트 실패 시 추가적인 '부상' 페널티 도입 고려"
    ],
    "balanceScore": 7.2
  }}
}}
"""
)
balance_analyzer_chain = LLMChain(llm=llm_analyzer, prompt=game_balance_prompt_template)


# -----------------------------------------------------------------------------
# 3. 로직 및 FastAPI 엔드포인트
# -----------------------------------------------------------------------------
def simple_simulation_logic(rule_id: int, player_names: List[str], max_turns: int, enable_penalty: bool) -> dict:
    rule_data = game_rules_database.get(rule_id)
    if not rule_data:
        raise HTTPException(status_code=404, detail=f"Rule ID {rule_id}에 해당하는 규칙을 찾을 수 없습니다.")

    rules_text = json.dumps(rule_data, ensure_ascii=False, indent=2)
    player_names_str = ", ".join(player_names)
    penalty_info_str = "적용됨" if enable_penalty else "적용되지 않음"

    try:
        response = enhanced_simulation_chain.invoke({
            "game_rules_text": rules_text,
            "player_names": player_names_str,
            "max_turns": max_turns,
            "penalty_info": penalty_info_str
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 체인 실행 중 오류 발생: {e}")

    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)
        if not json_match:
            raise ValueError("LLM 응답에서 유효한 JSON 요약 블록을 찾을 수 없습니다.")
        
        json_str = json_match.group(1).replace("{{", "{").replace("}}", "}")
        sim_result = json.loads(json_str)
        
        final_response = {
            "simulationHistory": [
                {
                    "gameId": 1,
                    "turns": sim_result.get("turns", []),
                    "winner": sim_result.get("winner", "N/A"),
                    "totalTurns": sim_result.get("totalTurns", 0),
                    "victoryCondition": sim_result.get("victoryCondition", "승리 조건 정보 없음"),
                    "durationMinutes": sim_result.get("durationMinutes", random.randint(15, 60)),
                    "score": sim_result.get("score", {})
                }
            ]
        }
        return final_response
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"오류: {e}\n원본 LLM 응답: {response['text']}")
        raise HTTPException(status_code=500, detail=f"LLM 응답 파싱 오류: {e}")

# --- Pydantic 모델 정의 ---
class SimpleSimulateRequest(BaseModel):
    ruleId: int = Field(..., example=101, description="시뮬레이션할 게임 규칙 ID")
    playerNames: List[str] = Field(..., example=["탐험가 A", "공학자 B"], description="참여 플레이어 이름 목록")
    maxTurns: int = Field(..., example=10, description="최대 시뮬레이션 턴 수")
    enablePenalty: bool = Field(..., example=True, description="페널티 규칙 적용 여부")

class ActionLog(BaseModel):
    player: str
    action: str
    details: str
    rationale: str

class TurnLog(BaseModel):
    turn: int
    actions: List[ActionLog]

class GameSimulationResult(BaseModel):
    gameId: int
    turns: List[TurnLog]
    winner: str
    totalTurns: int
    victoryCondition: str
    durationMinutes: int
    score: Dict[str, int]

class SimpleSimulateResponse(BaseModel):
    simulationHistory: List[GameSimulationResult]

# 밸런스 분석 응답 모델
class BalanceAnalysis(BaseModel):
    simulationSummary: str = Field(..., example="이 게임은 팀 플레이와 자원 관리가 중요한 협력 게임입니다. 예측 불가능한 외계 생명체 이벤트가 주요 변수가 될 것입니다.")
    issuesDetected: List[str] = Field(..., example=["'탐색' 액션의 성공 확률이 낮아 플레이어에게 좌절감을 줄 수 있습니다.", "'부품' 자원 확보 난이도에 비해 '방어 포탑' 건설 비용이 너무 높을 수 있습니다."])
    recommendations: List[str] = Field(..., example=["'탐색' 성공 시 최소한의 '에너지'라도 돌려받도록 수정하여 리스크를 줄입니다.", "'방어 포탑' 건설 비용을 '부품' 2개로 줄이거나, 건설 시 추가적인 방어 보너스를 부여합니다."])
    balanceScore: float = Field(..., example=7.5, description="게임 밸런스 평점 (10점 만점, 10이 완벽한 균형)")

class FeedbackBalanceResponse(BaseModel):
    balanceAnalysis: BalanceAnalysis

# --- FastAPI 엔드포인트 ---
@app.post("/api/simulate/rule-test", response_model=SimpleSimulateResponse, summary="간단한 규칙 시뮬레이션")
async def simple_simulate_api(request: SimpleSimulateRequest):
    """
    주어진 규칙과 플레이어 정보로 간단한 가상 플레이 로그를 생성합니다.
    """
    try:
        simulation_data = simple_simulation_logic(
            rule_id=request.ruleId,
            player_names=request.playerNames,
            max_turns=request.maxTurns,
            enable_penalty=request.enablePenalty
        )
        return simulation_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류 발생: {e}")

@app.get("/api/feedback/balance", response_model=FeedbackBalanceResponse, summary="게임 밸런스 분석 피드백 (LLM 기반)")
async def get_balance_feedback():
    """
    게임 규칙 101에 대한 LLM 기반 밸런스 분석 결과를 제공합니다.
    """
    rule_id = 101 # 현재는 고정된 Rule ID 101에 대해서만 밸런스 분석을 제공
    rule_data = game_rules_database.get(rule_id)
    if not rule_data:
        raise HTTPException(status_code=404, detail=f"Rule ID {rule_id}에 해당하는 규칙을 찾을 수 없습니다.")

    rules_text = json.dumps(rule_data, ensure_ascii=False, indent=2)

    try:
        response = balance_analyzer_chain.invoke({
            "game_rules_text": rules_text
        })
        
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)
        if not json_match:
            raise ValueError("LLM 응답에서 유효한 JSON 요약 블록을 찾을 수 없습니다.")
        
        json_str = json_match.group(1).replace("{{", "{").replace("}}", "}")
        balance_result = json.loads(json_str)

        # LLM 응답이 FeedbackBalanceResponse 모델 스키마와 일치하는지 확인하며 반환
        return FeedbackBalanceResponse(**balance_result)
        
    except (json.JSONDecodeError, ValueError) as e:
        print(f"오류: {e}\n원본 LLM 응답: {response['text']}")
        raise HTTPException(status_code=500, detail=f"LLM 응답 파싱 오류: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 기반 밸런스 분석 중 오류 발생: {e}")


# 이 코드가 직접 실행될 때만 uvicorn 서버를 시작합니다.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
