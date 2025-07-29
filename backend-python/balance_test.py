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
import random
import sys

# Langgraph 및 관련 라이브러리 임포트 (규칙 시뮬레이션용)
from typing import Dict, List, Literal, TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import END, START, StateGraph
import io # 시뮬레이션 로그 캡처용

# FastAPI 관련 라이브러리
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 설정 (환경 변수에서 가져오기)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

app = FastAPI(
    title="보드게임 기획 API",
    description="보드게임 컨셉 생성, 재생성, 구성요소 생성, 규칙 생성 및 규칙 재생성, 규칙 시뮬레이션 기능을 제공합니다.",
    version="1.1.0",
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
# -----------------------------------------------------------------------------
# 1-1. 컨셉 데이터 (컨셉 생성/재생성에 사용)
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

# 1-2. 컨셉, 세계관, 목표 통합 데이터 (목표, 규칙 생성에 사용)
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
    12: {
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

# 1-3. planId 기반 데이터베이스 (구성요소 생성에 사용)
plan_data_for_components = {
    item["concept"]["planId"]: item for item in concept_world_objective_database.values()
}
# 요청하신 planId 13에 대한 데이터 추가 (conceptId 12의 데이터와 동일)
if 12 in concept_world_objective_database:
    plan_data_for_components[concept_database_for_regen[12]["planId"]] = concept_world_objective_database[12]
# 임시 planId (1012)에 대한 가상의 데이터 추가 (구성요소 생성 요청 예시)
plan_data_for_components[1012] = {
    "concept": {
        "conceptId": 9999,
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
        "setting": { "era": "초월적인 시간", "location": "시간의 강, 과거와 미래의 주요 역사적 지점들", "factions": ["시간 수호자", "시간의 변칙", "기생 시간체"], "conflict": "역사 복구 vs 시간의 파괴" },
        "tone": "신비로운 / 시간 기반 퍼즐 / 모험"
    },
    "objective": {
        "mainGoal": "시간의 강에 흩어진 5개의 '크로노스 코어'를 모두 수집하여 시간의 흐름을 안정화하고, 역사를 원래대로 되돌리십시오.",
        "subGoals": ["특정 시대의 역사적 변칙 3가지 수정", "시간 조작 능력을 최대로 업그레이드", "시간의 균열 10개 봉인"],
        "winConditionType": "목표 달성형 / 퍼즐 해결형",
        "designNote": "시간의 흐름을 읽고 과거와 미래의 사건에 개입하는 전략적인 선택이 중요하며, 플레이어 간의 정보 공유와 협력이 필수적입니다."
    }
}


# 1-4. 게임 규칙 데이터 (규칙 생성/재생성/시뮬레이션에 사용)
game_rules_database = {
    2222: {
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
        "designNote": "게임 흐름이 직관적이면서도, 협상과 배신이 자연스럽게 녹아들도록 구조화함",
        # 시뮬레이션용 상세 규칙 텍스트 추가
        "full_rule_text_for_llm": """
        게임명: 에테르 크리스탈 전쟁
        장르: 전략, 영토 확장, 자원 관리
        플레이어 수: 2-4명
        플레이 시간: 60-90분
        대상 연령: 12세 이상

        1. 게임 개요:
        고대 제국의 후예들은 파괴된 대륙에 흩어진 전설의 유물 '에테르 크리스탈'을 차지하기 위해 턴제 전투를 벌입니다. 플레이어는 전략적인 지형을 활용하여 상대를 견제하고, 라운드마다 새로운 카드를 드래프트하여 유닛을 소환하며 영토를 확장하고 자원을 확보해야 합니다. 각 가문은 고유한 능력을 활용해 승리를 쟁취합니다.

        2. 턴 구조:
        각 턴은 다음 단계로 구성됩니다:
        - 1. 자원 수집 페이즈: 각 플레이어는 자신의 통제 하에 있는 영토와 건물에서 자원(금, 식량, 마나)을 획득합니다.
        - 2. 행동 선택 페이즈: 플레이어는 자신의 턴에 다음 중 하나의 주 행동을 선택하여 수행합니다:
            - 유닛 소환: 보유 자원을 소모하여 유닛 카드를 드래프트하고 유닛을 소환합니다.
            - 영토 확장: 인접한 중립 영토로 유닛을 이동시켜 영토를 점령하고 자원 생산량을 늘립니다.
            - 건물 건설: 자원을 소모하여 영토에 건물을 건설하고 추가 효과를 얻습니다 (예: 방어력 증가, 자원 생산 보너스).
            - 기술 연구: 특정 자원을 소모하여 새로운 능력이나 유닛을 해금합니다.
            - 공격/전투: 인접한 상대 영토의 유닛을 공격하여 점령을 시 시도합니다. 전투는 주사위 굴림과 유닛 능력치를 기반으로 합니다.
            - 교섭/동맹: 다른 플레이어와 자원 또는 영토 교환을 제안하고 일시적인 동맹을 맺을 수 있습니다.
        - 3. 전투/교섭 해결 페이즈: 모든 플레이어의 행동이 선언된 후, 충돌(전투) 및 교섭 결과를 처리합니다.
        - 4. 턴 종료 처리: 사용된 카드 및 자원을 정리하고 다음 플레이어에게 턴을 넘깁니다.

        3. 승리 조건:
        게임은 다음 중 하나의 조건이 충족되면 종료됩니다:
        - 유물 수집 승리: '에테르 크리스탈' 유물 토큰 3개를 먼저 수집한 플레이어가 즉시 승리합니다.
        - 영토 독점 승리: 맵의 모든 주요 거점(핵심 자원 지대 5곳)을 점령하고 2턴 동안 유지한 플레이어가 승리합니다.
        - 멸망 승리: 마지막으로 남은 플레이어가 승리합니다 (다른 모든 플레이어의 본거지가 점령되었을 때).

        4. 페널티 규칙:
        - 자원 고갈: 특정 자원이 0이 되면, 해당 자원을 사용하는 모든 행동은 수행할 수 없습니다.
        - 유닛 전멸: 모든 유닛이 파괴되면 다음 턴에 유닛을 소환할 수 없습니다 (본거지 방어 유닛 1개는 항상 유지).
        - 동맹 파기: 동맹을 일방적으로 파기할 경우, 다음 3턴간 모든 플레이어로부터 교섭을 거부당합니다.
        - 본거지 점령: 자신의 본거지가 점령당하면 해당 플레이어는 게임에서 패배합니다.

        5. 디자인 노트:
        플레이어는 자원 관리와 영토 확장을 통해 전략적인 깊이를 경험하며, 다양한 승리 조건으로 리플레이 가치를 높입니다. 전투와 교섭을 통한 플레이어 간의 상호작용이 게임의 핵심 재미입니다.
        """
    },
    23: {
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
        "designNote": "간단하고 빠른 턴 진행을 목표로 함",
        "full_rule_text_for_llm": """
        게임명: 미지의 던전 탐험
        장르: 던전 탐험, 자원 수집, 몬스터 전투
        플레이어 수: 1-4명
        플레이 시간: 30-60분
        대상 연령: 8세 이상

        1. 게임 개요:
        용감한 모험가들이 고대의 미궁에 들어가 숨겨진 보물을 찾고, 강력한 보스 몬스터를 물리쳐 던전을 정화하는 협동 게임입니다. 플레이어들은 이동과 행동 카드를 전략적으로 사용하여 자원을 모으고, 몬스터와 싸우며, 퍼즐을 해결해야 합니다.

        2. 턴 구조:
        각 플레이어의 턴은 다음 단계로 구성됩니다:
        - **1. 플레이어 턴 시작:** 플레이어는 자신의 턴 시작 효과(예: 잃은 체력 1 회복)를 발동합니다.
        - **2. 이동:** 플레이어는 자신의 모험가 미니어처를 인접한 공간으로 최대 1칸 이동할 수 있습니다. 특정 카드나 능력으로 추가 이동이 가능합니다.
        - **3. 행동 (택 1):** 플레이어는 다음 중 하나의 주 행동을 선택하여 수행합니다:
            - **자원 수집:** 현재 위치한 던전 타일(광산, 숲, 유적 등)에 표시된 자원 토큰(금, 약초, 고대 파편) 1개를 획득합니다.
            - **카드 사용:** 손에 있는 행동 카드 1장을 사용하여 카드에 명시된 효과(예: "추가 이동", "몬스터 공격", "함정 해제")를 발동합니다. 사용된 카드는 버림 더미로 갑니다.
            - **휴식:** 잃은 체력 2를 회복하고, 버림 더미의 카드 2장을 손으로 가져옵니다.
        - **4. 몬스터 활성화:** 던전에 있는 모든 몬스터가 활성화되어 가장 가까운 플레이어에게 이동하거나 공격합니다. 전투는 주사위 굴림으로 판정됩니다.
        - **5. 턴 종료:** 플레이어는 손에 있는 카드 수를 제한(기본 5장)까지 맞추고, 다음 플레이어에게 턴을 넘깁니다.

        3. 승리 조건:
        - 맵 중앙에 위치한 '고대 보스 몬스터'를 성공적으로 처치하면 모든 플레이어가 승리합니다.

        4. 페널티 규칙:
        - **체력 0:** 모험가의 체력이 0이 되면, 해당 모험가는 모든 자원을 잃고 다음 1턴을 쉴 수밖에 없습니다.
        - **함정 발동:** 함정 타일에 진입하거나 특정 이벤트 카드에 의해 함정이 발동하면, 체력 피해를 입거나 강제 이동 또는 카드 상실 등의 페널티를 받습니다.
        - **시간 제한:** 특정 턴 수(예: 15턴)가 지나면 던전이 붕괴하기 시작하여 매 턴 추가 피해를 입습니다.

        5. 디자인 노트:
        간단한 규칙으로 빠르게 던전 탐험의 재미를 느낄 수 있도록 설계되었습니다. 몬스터와의 전투와 자원 관리가 주요 전략 요소이며, 협동을 통해 난관을 극복하는 것이 중요합니다.
        """
    },
    3105: {
        "ruleId": 3105,
        "turnStructure": "1. 시간 에너지 수급 페이즈 → 2. 행동 선택 페이즈 → 3. 정리 페이즈",
        "actionRules": [
            "자원 수집 (gather_X)", "건물 건설", "유닛 생산 (build_unit)", "유물 탐색",
            "기술 연구", "공격 (attack_opponent)", "시간 에너지 조율 (특수 행동)"
        ],
        "victoryCondition": "최대 턴 도달 시 또는 특정 즉시 승리 조건 달성 시 가장 높은 크로노스 점수를 획득",
        "penaltyRules": [
            "문명 HP가 0이 되면 게임에서 패배",
            "시간 에너지 고갈 시 특정 행동에 제약 발생"
        ],
        "designNote": "시간 자원 관리와 유물/기술 발전을 통한 문명 건설 및 경쟁 강조",
        # 시뮬레이션용 상세 규칙 텍스트 (밸런스_테스트.ipynb에서 가져옴)
        "full_rule_text_for_llm": """
            보드게임 기획서: 크로노스의 유산 (Chronos' Legacy)
            게임명: 크로노스의 유산: 시간의 조율자들 (Chronos' Legacy: The Chrono-Harmonizers)
            장르: 전략, 자원 관리, 문명 발전, 영역 확장
            플레이어 수: 2-4 인
            플레이 시간: 60-90 분
            대상 연령: 12 세 이상

            1. 게임 개요 (Game Overview)
            오래전, 시간의 신 크로노스는 필멸자들에게 시간을 다스리는 힘의 일부를 부여했습니다. 그러나 이 힘은 남용되어 시간의 흐름이 불안정해졌고, 세계는 혼돈에 빠졌습니다. 플레이어들은 '시간의 조율자'가 되어 파편화된 시간의 흐름을 안정시키고, 자신만의 문명을 발전시키며, 진정한 크로노스의 후계자가 되기 위한 경쟁을 벌입니다. 다양한 시대의 유물을 수집하고, 시간 에너지(Temporal Energy)를 효율적으로 관리하여 가장 강력하고 조화로운 문명을 건설하는 것이 목표입니다.
            핵심 특징:
            • 시간 자원 관리: '시간 에너지'라는 독특한 자원을 사용하여 행동 우선순위를 정하고, 과거/미래의 행동을 미리 계획하거나 되돌리는 등 전략적인 선택을 강요합니다.
            • 유물 수집 및 능력 획득: 고대부터 미래까지 다양한 시대의 강력한 유물을 수집하여 문명에 고유한 능력을 부여하고 발전시킵니다.
            • 테크 트리 발전: 여러 시대의 기술을 연구하여 새로운 건물, 유닛, 능력을 잠금 해제하며 문명을 심화시킵니다.
            • 비대칭 능력: 각 플레이어는 시작 시 선택하는 '조율자' 종족에 따라 고유한 시작 능력과 목표를 가집니다. (예: 엘프 - 시간 에너지 효율, 드워프 - 유물 채굴 특화, 인간 - 빠른 확장)
            • 다양한 승리 조건: 단순히 점수를 높이는 것을 넘어, 특정 유물 세트 완성, 시간 에너지 독점, 특정 시대 기술 완성 등 다양한 승리 경로를 제공하여 리플레이성을 높입니다.

            2. 게임 목표 (Game Objective)
            정해진 턴(시대)이 종료되었을 때, 또는 특정 즉시 승리 조건을 달성했을 때, 가장 높은 크로노스 점수 (Chronos Score)를 획득한 플레이어가 승리합니다.
            크로노스 점수 획득 방법:
            • 건물 건설 (가치에 따라 차등 점수)
            • 유물 수집 (세트 완성 시 보너스 점수)
            • 시대 연구 완료
            • 영토 확장 및 특정 지역 통제
            • 각 조율자 종족의 고유 목표 달성
            즉시 승리 조건 (예시):
            • 모든 플레이어의 문명 HP 를 0 으로 만들었을 때 (군사 승리)
            • 모든 시대의 최상위 기술을 연구했을 때 (기술 승리)
            • 특정 희귀 유물 세트 3 개 이상을 완성했을 때 (유물 승리)

            3. 구성 요소 (Game Components)
            • 게임 보드:
            o 중앙 '시간의 소용돌이' (액션 선택 트랙)
            o 시대별 기술 연구 트랙 (고대, 중세, 근대, 미래)
            o 자원 생산 지역 (크리스탈 광산, 고대 숲, 황금 유적 등)
            o 건설 가능한 지역 (도시, 요새, 신비의 탑 등)
            • 플레이어 보드 (4 개):
            o 자원 보관 구역 (금, 나무, 식량, 크리스탈)
            o 시간 에너지 트랙 및 보관 구역
            o 유닛 배치 및 관리 구역
            o 건설된 건물 및 연구된 기술 표시 구역
            o 조율자 종족 특성 표시 구역
            • 카드:
            o 유물 카드 (약 50 장): 시대별 유물 (고대 유물, 중세 유물, 미래 기술 등)
            o 행동 카드 (약 30 장): 매 턴 선택 가능한 특별 행동 또는 이벤트
            o 이벤트 카드 (약 20 장): 특정 턴 또는 조건에 따라 발생하는 전역 이벤트
            o 초기 조율자 카드 (4 장): 각 플레이어가 선택하는 종족 (엘프, 드워프, 인간, 기계)
            • 토큰 및 마커:
            o 자원 토큰 (금, 나무, 식량, 크리스탈)
            o 시간 에너지 토큰
            o 문명 HP 마커
            o 플레이어 순서 마커
            o 점수 마커
            o 유닛 마커 (각 종족별 특색 있는 모양)
            • 주사위: 6 면체 주사위 2 개 (전투 및 특정 행동 결과 판정용)

            4. 게임 플레이 (Gameplay)
            A. 게임 준비:
            1. 게임 보드를 중앙에 펼치고 '시간의 소용돌이' 마커를 1 시대에 놓습니다.
            2. 각 플레이어는 조율자 카드 1 장과 해당 종족의 초기 자원, 유닛을 받습니다.
            3. 유물 카드 덱, 행동 카드 덱, 이벤트 카드 덱을 잘 섞어 보드에 배치합니다.
            4. 각 플레이어는 개인 보드를 받고 초기 자원을 세팅합니다.
            5. 무작위로 시작 플레이어를 정하고, 턴 순서를 결정합니다.
            B. 게임 턴 진행:
            게임은 총 20 시대로 진행됩니다. 각 시대(턴)는 다음 페이즈로 구성됩니다:
            1. 시간 에너지 수급 페이즈:
            o 각 플레이어는 자신의 문명 보드에 표시된 '시간 에너지' 및 기본 자원을 획득합니다.
            o 이벤트 카드 1 장을 공개하고, 카드에 따라 전역 효과를 적용합니다.
            2. 행동 선택 페이즈:
            o 시작 플레이어부터 순서대로, 자신의 턴에 1 가지 주 행동을 선택하고 수행합니다.
            o 주요 행동 (예시):
            ▪ 자원 수집: 보드 특정 지역에서 자원을 획득합니다. (예: 금, 나무, 식량)
            ▪ 건물 건설: 자원을 소모하여 자신의 영토에 건물을 짓습니다. 건물은 자원 생산량 증가, 유닛 생산 능력, 문명 HP 증가 등 다양한 효과를 가집니다.
            ▪ 유닛 생산: 병영 등에서 유닛을 생산합니다. 유닛은 전투력, 방어력, 이동력 등의 스탯을 가집니다.
            ▪ 유물 탐색: 유물 카드 덱에서 유물 카드를 뽑습니다.
            ▪ 기술 연구: 기술 연구 트랙에서 다음 시대의 기술을 연구합니다. 자원과 '시간 에너지'를 소모하며, 연구가 완료되면 새로운 건물, 유닛, 행동 등이 잠금 해제됩니다.
            ▪ 공격: 유닛을 사용하여 다른 플레이어의 영토나 문명을 공격합니다. 전투는 플레이어의 유닛 공격력 합계와 상대방의 유닛 방어력 합계를 비교하여 피해량을 계산하고, 주사위 보정을 적용하여 상대 문명 HP 를 감소시킵니다.
            ▪ 시간 에너지 조율 (특수 행동): 보유한 '시간 에너지'를 소모하여 특정 행동의 효율을 높이거나, 이미 발생한 행동을 일부 되돌리는 등의 능력을 사용합니다.
            o 선택된 행동에 필요한 자원을 지불하고, 행동의 효과를 적용합니다.
            3. 정리 페이즈:
            o 모든 플레이어가 행동을 마쳤으면, 사용된 '시간 에너지'를 재조정하고, 게임 보드의 '시간의 소용돌이' 마커를 다음 시대로 이동시킵니다.
            o 패배 조건을 확인하여 패배한 플레이어가 있는지 확인합니다.
            C. 게임 종료:
            • 최대 턴(시대) 도달: 20 시대에 도달하면 게임이 즉시 종료됩니다.
            • 즉시 승리 조건 달성: 특정 플레이어가 위에 명시된 즉시 승리 조건 중 하나를 달성하면, 게임이 즉시 종료되고 해당 플레이어가 승리합니다.
            D. 승자 결정:
            게임 종료 시, 각 플레이어는 최종 크로노스 점수를 합산하고, 가장 높은 점수를 가진 플레이어가 승리합니다. (동점일 경우 남은 시간 에너지, 유닛 수, 자원량 등 부가적인 규칙으로 승자를 판정)
            """
    }
}


# -----------------------------------------------------------------------------
# 2. LLM 설정 및 프롬프트 정의 (모든 기능에서 공통 사용)
# -----------------------------------------------------------------------------
llm_default = ChatOpenAI(model_name="gpt-4o", temperature=0.7)


# -----------------------------------------------------------------------------
# 3. 각 기획 기능별 LLM 체인 및 로직 함수
# -----------------------------------------------------------------------------

# 3-2. 컨셉 재생성 (기존 컨셉 피드백 반영)
regenerate_concept_prompt_template = PromptTemplate(
    input_variables=["original_concept_json", "feedback", "plan_id"],
    template="""당신은 보드게임 컨셉 디자이너입니다.
    주어진 기존 보드게임 컨셉에 대한 사용자 피드백을 바탕으로,
    **기존 컨셉을 수정하거나 완전히 새로운 컨셉을 한국어로 생성**해주세요.
    특히 피드백의 내용을 적극적으로 반영해야 합니다.

    재생성된 컨셉은 다음 형식으로 제공되어야 하며, 새로운 conceptId를 부여해야 합니다.
    이때 planId는 기존의 planId를 그대로 사용합니다.

    ---
    **기존 보드게임 컨셉 정보:**
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
      "conceptId": [새롭게 부여할 고유한 정수 ID (예: 1003, 1004 등)],
      "planId": {plan_id},
      "theme": "[새 컨셉의 테마 (한국어)]",
      "playerCount": "[새 컨셉의 플레이어 수 (예: '2~4명', '1명', '3~6명')]",
      "averageWeight": [새 컨셉의 평균 난이도 (1.0~5.0 사이의 실수)],
      "ideaText": "[새 컨셉의 핵심 아이디어 (한국어)]",
      "mechanics": "[새 컨셉의 주요 메커니즘 목록 (콤마로 구분, 한국어)]",
      "storyline": "[새 컨셉의 간략한 스토리라인 (한국어)]",
      "createdAt": "[이 필드는 LLM이 채우지 않고, 호출하는 코드에서 현재 시간으로 채웁니다.]"
    }}
    ```
    """
)
regenerate_concept_chain = LLMChain(llm=llm_default, prompt=regenerate_concept_prompt_template)

def regenerate_board_game_concept_logic(request_data: dict) -> dict:
    concept_id_to_regenerate = request_data.get("conceptId")
    feedback = request_data.get("feedback", "")
    plan_id = request_data.get("planId")

    original_concept_data = concept_database_for_regen.get(concept_id_to_regenerate)
    if not original_concept_data:
        raise HTTPException(status_code=404, detail=f"Concept ID {concept_id_to_regenerate}에 해당하는 원본 데이터를 찾을 수 없습니다.")

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

            # 현재 시간 KST (서울 기준)로 변경
            kst_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
            regenerated_concept["createdAt"] = kst_now.isoformat(timespec='seconds')

            new_concept_id = regenerated_concept.get("conceptId")
            if new_concept_id:
                if isinstance(new_concept_id, int) and new_concept_id not in concept_database_for_regen:
                    concept_database_for_regen[new_concept_id] = regenerated_concept
                    print(f"새로운 컨셉 (ID: {new_concept_id})이 데이터베이스에 추가되었습니다.")
                else:
                    max_id = max(concept_database_for_regen.keys()) if concept_database_for_regen else 0
                    new_unique_id = max(max_id + 1, 1000)
                    regenerated_concept["conceptId"] = new_unique_id
                    regenerated_concept["createdAt"] = kst_now.isoformat(timespec='seconds')
                    concept_database_for_regen[new_unique_id] = regenerated_concept
                    print(f"경고: LLM이 유효하지 않거나 중복된 conceptId ({new_concept_id})를 생성했습니다. 새로운 ID ({new_unique_id})로 할당합니다.")
            else:
                max_id = max(concept_database_for_regen.keys()) if concept_database_for_regen else 0
                new_unique_id = max(max_id + 1, 1000)
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


# 3-3. 게임 목표 생성
game_objective_prompt_template = PromptTemplate(
    input_variables=["theme", "playerCount", "averageWeight", "ideaText", "mechanics", "storyline", "world_setting", "world_tone"],
    template="""당신은 보드게임 디자이너입니다.
    주어진 보드게임 컨셉과 세계관 정보를 바탕으로 구체적이고 매력적인 **한국어** 게임 목표를 설계해주세요.
    플레이어가 게임에서 무엇을 달성해야 승리하는지 명확하게 제시해야 합니다.
    특히 게임의 핵심 아이디어, 메커니즘, 그리고 세계관에 부합하는 목표여야 합니다.

    ---
    **보드게임 컨셉 및 세계관 정보:**
    테마: {theme}
    플레이 인원수: {playerCount}
    난이도: {averageWeight}
    핵심 아이디어: {ideaText}
    주요 메커니즘: {mechanics}
    기존 스토리라인: {storyline}
    세계관 설정: {world_setting}
    세계관 분위기: {world_tone}
    ---

    당신은 다음 JSON 형식으로만 응답해야 합니다. **다른 어떤 설명이나 추가적인 텍스트도 포함하지 마세요.**
    모든 내용은 **한국어**로 작성되어야 합니다.

    ```json
    {{
      "mainGoal": "[플레이어가 게임에서 궁극적으로 달성해야 할 주요 목표를 구체적으로 설명 (한국어)]",
      "subGoals": [
        "[승리에 기여할 수 있는 보조 목표 1 (선택 사항) (한국어)]",
        "[승리에 기여할 수 있는 보조 목표 2 (선택 사항) (한국어)]"
      ],
      "winConditionType": "[승리 조건 유형 (예: 목표 달성형, 생존형, 점수 경쟁형 등)]",
      "designNote": "[게임 목표 설계에 대한 간략한 디자이너 노트 또는 의도 설명 (한국어)]"
    }}
    ```
    """
)
game_objective_chain = LLMChain(llm=llm_default, prompt=game_objective_prompt_template)

def generate_game_objective_logic(concept_id: int) -> dict:
    data_entry = concept_world_objective_database.get(concept_id)
    if not data_entry:
        raise HTTPException(status_code=404, detail=f"Concept ID {concept_id}에 해당하는 데이터를 찾을 수 없습니다.")

    concept_data = data_entry.get("concept", {})
    world_data = data_entry.get("world", {})

    world_setting_str = json.dumps(world_data.get("setting", {}), ensure_ascii=False) if world_data.get("setting") else ""

    try:
        response = game_objective_chain.invoke({
            "theme": concept_data.get("theme", ""),
            "playerCount": concept_data.get("playerCount", ""),
            "averageWeight": concept_data.get("averageWeight", 0.0),
            "ideaText": concept_data.get("ideaText", ""),
            "mechanics": concept_data.get("mechanics", ""),
            "storyline": concept_data.get("storyline", ""),
            "world_setting": world_setting_str,
            "world_tone": world_data.get("tone", "")
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 체인 실행 중 오류 발생: {e}")

    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            game_objective = json.loads(json_str)
            return game_objective
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


# 3-4. 구성요소 생성
component_generation_prompt_template = PromptTemplate(
    input_variables=["theme", "playerCount", "averageWeight", "ideaText", "mechanics", "storyline", "mainGoal", "winConditionType", "world_setting", "world_tone"],
    template="""당신은 보드게임의 구성요소(컴포넌트) 디자이너입니다.
    주어진 보드게임 컨셉, 목표 및 세계관 정보를 바탕으로,
    게임 플레이에 필수적이고 테마에 잘 어울리는 **한국어** 구성요소를 5개 이상 제안해주세요.
    각 구성요소는 다음 속성을 포함하는 JSON 객체여야 합니다.

    ---
    **보드게임 컨셉 정보:**
    테마: {theme}
    플레이 인원수: {playerCount}
    난이도: {averageWeight}
    핵심 아이디어: {ideaText}
    주요 메커니즘: {mechanics}
    스토리라인: {storyline}

    **게임 목표 정보:**
    주요 목표: {mainGoal}
    승리 조건 유형: {winConditionType}

    **세계관 정보:**
    세계관 설정: {world_setting}
    세계관 분위기: {world_tone}
    ---

    당신은 다음 JSON 형식으로만 응답해야 합니다. **다른 어떤 설명이나 추가적인 텍스트도 포함하지 마세요.**
    모든 내용은 **한국어**로 작성되어야 합니다.
    'effect'는 게임 내에서 해당 구성요소가 어떤 역할을 하는지 구체적으로 설명해주세요.
    'visualType'은 '2D' (카드, 보드, 타일 등) 또는 '3D' (미니어처, 토큰, 주사위 등) 중 하나로 선택해주세요.

    ```json
    {{
      "components": [
        {{
          "type": "[구성요소 유형 (예: 카드, 토큰, 보드, 주사위, 미니어처, 타일 등)]",
          "name": "[구성요소 이름 (한국어)]",
          "effect": "[게임 내에서 구성요소의 역할/효과 (한국어)]",
          "visualType": "[2D 또는 3D]"
        }},
        {{
          "type": "토큰",
          "name": "시간 조각 토큰",
          "effect": "점수 계산에 사용됩니다. (예시)",
          "visualType": "3D"
        }},
        // 최소 5개 이상 다양한 구성요소 제안
      ]
    }}
    ```
    """
)
component_generation_chain = LLMChain(llm=llm_default, prompt=component_generation_prompt_template)

def generate_game_components_logic(plan_id: int) -> dict:
    data_entry = plan_data_for_components.get(plan_id)
    if not data_entry:
        raise HTTPException(status_code=404, detail=f"Plan ID {plan_id}에 해당하는 컨셉/목표 데이터를 찾을 수 없습니다.")

    concept_data = data_entry.get("concept", {})
    world_data = data_entry.get("world", {})
    objective_data = data_entry.get("objective", {})

    world_setting_str = json.dumps(world_data.get("setting", {}), ensure_ascii=False) if world_data.get("setting") else ""

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

    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            components_data = json.loads(json_str)
            if "components" not in components_data or not isinstance(components_data["components"], list):
                raise ValueError("LLM 응답에 'components' 리스트가 포함되어 있지 않거나 형식이 올바르지 않습니다.")
            return components_data
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


# 3-5. 게임 규칙 생성
game_rules_prompt_template = PromptTemplate(
    input_variables=["theme", "playerCount", "averageWeight", "ideaText", "mechanics",
                     "storyline", "world_setting", "world_tone",
                     "mainGoal", "subGoals", "winConditionType", "objective_designNote"],
    template="""당신은 보드게임 규칙 전문가입니다.
    주어진 보드게임의 컨셉, 세계관, 그리고 게임 목표 정보를 바탕으로 구체적이고 명확한 **한국어** 게임 규칙을 설계해주세요.
    게임의 핵심 플레이 흐름, 행동 규칙, 승리 조건, 그리고 패널티 규칙을 상세하게 제시해야 합니다.
    제시된 게임 목표와 컨셉, 메커니즘이 잘 연동되도록 규칙을 구상해주세요.

    ---
    **보드게임 컨셉 및 세계관 정보:**
    테마: {theme}
    플레이 인원수: {playerCount}
    난이도: {averageWeight}
    핵심 아이디어: {ideaText}
    주요 메커니즘: {mechanics}
    기존 스토리라인: {storyline}
    세계관 설정: {world_setting}
    세계관 분위기: {world_tone}

    **보드게임 목표 정보:**
    주요 목표: {mainGoal}
    보조 목표: {subGoals}
    승리 조건 유형: {winConditionType}
    목표 설계 노트: {objective_designNote}
    ---

    당신은 다음 JSON 형식으로만 응답해야 합니다. **다른 어떤 설명이나 추가적인 텍스트도 포함하지 마세요.**
    모든 내용은 **한국어**로 작성되어야 합니다.
    ruleId는 임의의 고유한 정수 ID로 부여해야 합니다.

    ```json
    {{
      "ruleId": [고유한 정수 ID (예: 2222, 2223 등)],
      "turnStructure": "[게임의 각 턴이 어떤 단계로 구성되는지 순서대로 설명 (예: 1. 자원 수집 → 2. 행동 선택 → 3. 전투 또는 협상 → 4. 턴 종료 처리)]",
      "actionRules": [
        "[플레이어가 턴에 할 수 있는 주요 행동 1에 대한 구체적인 규칙 (한국어)]",
        "[플레이어가 턴에 할 수 있는 주요 행동 2에 대한 구체적인 규칙 (한국어)]"
      ],
      "victoryCondition": "[게임의 최종 승리 조건 및 판정 방식 (게임 목표의 'mainGoal'과 'winConditionType'을 구체적인 규칙으로 변환) (한국어)]",
      "penaltyRules": [
        "[플레이어가 특정 상황에서 받게 되는 페널티 1 (한국어)]",
        "[플레이어가 특정 상황에서 받게 되는 페널티 2 (한국어)]"
      ],
      "designNote": "[게임 규칙 설계에 대한 간략한 디자이너 노트 또는 의도 설명 (한국어)]"
    }}
    ```
    """
)
game_rules_chain = LLMChain(llm=llm_default, prompt=game_rules_prompt_template)

def generate_game_rules_logic(concept_id: int) -> dict:
    data_entry = concept_world_objective_database.get(concept_id)
    if not data_entry:
        raise HTTPException(status_code=404, detail=f"Concept ID {concept_id}에 해당하는 데이터를 찾을 수 없습니다.")

    concept_data = data_entry.get("concept", {})
    world_data = data_entry.get("world", {})
    objective_data = data_entry.get("objective", {})

    world_setting_str = json.dumps(world_data.get("setting", {}), ensure_ascii=False) if world_data.get("setting") else ""
    sub_goals_str = ", ".join(objective_data.get("subGoals", []))

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

    try:
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response['text'], re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            game_rules = json.loads(json_str)

            if not isinstance(game_rules.get("ruleId"), int):
                game_rules["ruleId"] = int(datetime.datetime.now().timestamp() * 1000) % 1000000 + 1000

            # 생성된 규칙을 데이터베이스에 추가 (재생성을 위해)
            game_rules_database[game_rules["ruleId"]] = game_rules
            print(f"새로운 규칙 (ID: {game_rules['ruleId']})이 데이터베이스에 추가되었습니다.")

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


# 3-6. 게임 규칙 재생성
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
regenerate_rules_chain = LLMChain(llm=llm_default, prompt=regenerate_rules_prompt_template)

def regenerate_game_rules_logic(request_data: dict) -> dict:
    rule_id_to_regenerate = request_data.get("ruleId")
    feedback = request_data.get("feedback", "")

    original_rule_data = game_rules_database.get(rule_id_to_regenerate)
    if not original_rule_data:
        raise HTTPException(status_code=404, detail=f"Rule ID {rule_id_to_regenerate}에 해당하는 원본 규칙 데이터를 찾을 수 없습니다.")

    # LLM에 전달할 JSON 문자열을 생성 (full_rule_text_for_llm은 재생성 프롬프트에 불필요)
    original_rule_for_llm = {k: v for k, v in original_rule_data.items() if k != "full_rule_text_for_llm"}
    original_rule_json_str = json.dumps(original_rule_for_llm, indent=2, ensure_ascii=False)

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
            regenerated_rules["ruleId"] = rule_id_to_regenerate # ruleId는 기존 것을 유지

            # 재생성된 규칙의 요약 부분만 업데이트하고, full_rule_text_for_llm은 새로운 LLM 호출로 생성할 수도 있음
            # 여기서는 단순히 LLM이 재생성한 요약 JSON만 반환합니다.
            # 필요하다면 regenerated_rules_database[rule_id_to_regenerate] = regenerated_rules 로 업데이트 가능

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


# 3-7. 게임 규칙 시뮬레이션 관련 LLM 설정 및 함수
# --- 상태 정의 (밸런스 테스트.ipynb에서 가져옴) ---
class GameSimState(TypedDict):
    game_rules_text: str
    game_summary: str
    game_keywords: List[str]
    player_roles: List[Dict]
    turn_unit: str
    simulation_strategy: str
    turn_log: List[str]
    current_turn: int
    max_turns: int
    player_states: List[Dict]
    single_game_evaluation: str
    all_evaluations_log: List[str]
    final_report: str
    next_step: Literal["simulate_turn", "evaluate_single_game", "end_simulation"]
    player_count_override: int

# --- 그래프 노드 함수 (밸런스 테스트.ipynb에서 가져옴) ---
def analyze_game_rules(state: GameSimState) -> GameSimState:
    print("🤖 [분석] 게임 규칙 분석 및 정보 추출 중...")
    parser = JsonOutputParser()
    prompt = ChatPromptTemplate.from_template("""
        당신은 보드게임 규칙 텍스트를 분석하여 JSON 형식으로만 출력하는 시스템입니다.
        주어진 게임 규칙 텍스트를 읽고, 아래 JSON 형식에 맞춰 **모든 정보를 정확히 추출**해주세요.

        **[규칙]**
        - 응답은 반드시 ` ```json ... ``` ` 코드 블록 안에 유효한 JSON 객체만 포함해야 합니다.
        - JSON 객체 외에 어떤 설명, 인사, 추가적인 텍스트도 절대 포함해서는 안 됩니다.

        **[게임 규칙 텍스트]**
        {game_rules_text}

        **[출력 JSON 형식]**
        ```json
        {{
            "summary": "게임의 핵심 컨셉, 메커니즘, 승리 조건 등을 기획자가 이해하기 쉽게 15문장 내외로 상세히 요약",
            "keywords": ["게임의 개성과 밸런스에 영향을 주는 핵심 키워드 15개"],
            "turn_unit": "게임에서 턴을 세는 단위 (예: 시대, 라운드)",
            "player_roles": [
                {{"name": "역할 이름1", "description": "해당 역할의 고유 능력 또는 특징에 대한 상세한 설명"}},
                {{"name": "역할 이름2", "description": "해당 역할의 고유 능력 또는 특징에 대한 상세한 설명"}}
            ]
        }}
        ```
    """)
    chain = prompt | llm_default | parser
    analysis_result = chain.invoke({"game_rules_text": state["game_rules_text"]})
    state["game_summary"] = analysis_result.get("summary", "")
    state["game_keywords"] = analysis_result.get("keywords", [])
    state["player_roles"] = analysis_result.get("player_roles", [])
    state["turn_unit"] = analysis_result.get("turn_unit", "턴")
    return state

def generate_simulation_strategy(state: GameSimState) -> GameSimState:
    print("🧭 [전략] 시뮬레이션 테스트 전략 수립 중...")
    prompt = ChatPromptTemplate.from_template("""
        당신은 게임 밸런스 테스트 전문가입니다. 아래 게임 정보와 플레이어 역할을 바탕으로,
        이 게임의 밸런스를 효과적으로 검증할 수 있는 **3가지 구체적인 테스트 전략**을 세워주세요.
        각 전략은 어떤 부분을 집중적으로 확인할 것인지 명확하게 서술해야 합니다.

        # 게임 요약
        {summary}
        # 핵심 키워드
        {keywords}
        # 플레이어 역할
        {roles}
    """)
    chain = prompt | llm_default
    roles_info = json.dumps(state["player_roles"], ensure_ascii=False, indent=2)
    simulation_strategy = chain.invoke({
        "summary": state["game_summary"],
        "keywords": ", ".join(state["game_keywords"]),
        "roles": roles_info
    }).content
    state["simulation_strategy"] = simulation_strategy
    return state

def start_new_game(state: GameSimState) -> GameSimState:
    print("새로운 게임 시뮬레이션을 위한 상태 초기화 중...")
    num_players_override = state.get("player_count_override")
    
    state["current_turn"] = 0
    state["turn_log"] = []

    player_roles = state.get("player_roles", [])
    player_states = []

    if player_roles and num_players_override and num_players_override <= len(player_roles):
        selected_roles = random.sample(player_roles, num_players_override)
        print(f"   > {num_players_override}명의 플레이어가 선택된 고유 역할로 게임을 시작합니다.")
        for i, role in enumerate(selected_roles):
            player_states.append({
                "id": i + 1,
                "role": role.get("name"),
                "strategy": f"{role.get('description')} 특징을 극대화하는 방향으로 플레이",
                "status": "게임 초반, 자원 확보 및 기반 마련 중"
            })
    elif num_players_override:
        print(f"   > 고유 역할이 부족하거나 없어, {num_players_override}명의 일반 플레이어로 게임을 시작합니다.")
        for i in range(num_players_override):
            player_states.append({
                "id": i + 1,
                "role": f"플레이어 {i+1}",
                "strategy": "일반적인 승리 조건을 최적의 경로로 달성",
                "status": "게임 초반, 자원 확보 및 기반 마련 중"
            })
    else:
        num_players_default = 3
        print(f"   > 플레이어 수 정보가 없어, {num_players_default}명의 일반 플레이어로 게임을 시작합니다.")
        for i in range(num_players_default):
            player_states.append({
                "id": i + 1,
                "role": f"플레이어 {i+1}",
                "strategy": "일반적인 승리 조건을 최적의 경로로 달성",
                "status": "게임 초반, 자원 확보 및 기반 마련 중"
            })

    state["player_states"] = player_states
    print(f"   > 이번 게임 플레이어: {[p['role'] for p in player_states]}")
    return state

def simulate_turn(state: GameSimState) -> GameSimState:
    state["current_turn"] += 1
    turn = state["current_turn"]
    turn_unit = state["turn_unit"]
    print(f"🔄 {turn}번째 {turn_unit} 시뮬레이션 진행...")

    prompt = ChatPromptTemplate.from_template("""
        당신은 한 편의 소설을 쓰는 작가이자, 보드게임을 진행하는 게임 마스터(GM)입니다.
        현재는 {turn}번째 {turn_unit}입니다. 이 턴에 각 플레이어가 어떤 행동을 할지, 게임을 한 번도 해보지 않은 기획자도 그 상황에 완전히 몰입할 수 있도록 생생하고 상세한 한 편의 장면을 묘사해주세요.

        [묘사 지침]
        1.  **플레이어의 내면 묘사:** 각 플레이어의 현재 상황, 고민, 전략적 목표, 감정(초조함, 희열, 의심 등)을 깊이 있게 서술하세요.
        2.  **행동의 구체화:** '자원을 얻었다'가 아니라, '엘프는 고대 숲의 신비로운 기운을 받아 마나 수정을 3개 획득했다'처럼 구체적이고 테마에 맞는 묘사를 사용하세요.
        3.  **상호작용과 분위기:** 플레이어 간의 견제, 협력, 대립 관계를 드러내고, 게임의 전체적인 분위기(긴장감, 평화, 혼돈 등)를 조성해주세요.
        4.  **결과의 영향:** 한 플레이어의 행동이 다른 플레이어와 게임 전체에 어떤 파급효과를 가져왔는지 연결해서 서술해주세요.

        # 게임 배경 및 테스트 전략
        {strategy}

        # 현재 플레이어 상태
        {player_states}

        [묘사 예시]
        {turn}번째 {turn_unit}
        **엘프 조율자 (플레이어 1):**
        엘프는 초조한 눈빛으로 자신의 플레이어 보드를 내려다보았다. '젠장, 시간 에너지가 바닥을 보이는군. 드워프가 저렇게 유물을 모아대다니... 여기서 한 턴만 더 지체되면 따라잡을 수 없게 될 거야.' 그는 잠시 고민하다, 위험을 감수하기로 결심했다. "미래의 힘을 빌리겠다!" 그는 '시간 가속' 능력을 사용하여 다음 턴의 자원 일부를 미리 획득했다. 이 행동으로 그의 문명은 일시적으로 불안정해졌지만, 이번 턴에 강력한 '시간의 탑'을 건설할 마지막 기회를 잡았다. 탑에서 뿜어져 나오는 푸른빛이 그의 영토를 감쌌다.

        **드워프 채굴자 (플레이어 2):**
        "하하하! 보아라, 이것이 바로 고대의 힘이다!\" 드워프는 방금 유물 탐사를 통해 얻은 '대지의 심장'을 높이 치켜들었다. 주변의 인간과 기계 플레이어들의 얼굴에는 부러움과 경계심이 스쳤다. 이 유물은 매 턴 금을 추가로 생산해 주는 강력한 효과를 지녔다. 드워프는 이 막강한 자금력으로 '강철 골렘' 부대를 생산하기 시작했다. 그의 영토에는 이제 강력한 골렘들이 우뚝 서, 누구든 침범하면 대가를 치를 것이라는 무언의 압박을 가하고 있었다.
    """)
    chain = prompt | llm_default
    turn_result = chain.invoke({
        "turn": turn,
        "turn_unit": turn_unit,
        "strategy": state["simulation_strategy"],
        "player_states": json.dumps(state["player_states"], ensure_ascii=False)
    }).content
    state["turn_log"].append(turn_result)
    for player in state["player_states"]:
        player["status"] = f"{turn}번째 {turn_unit} 행동 완료"
    return state

def evaluate_and_decide(state: GameSimState) -> GameSimState:
    if state["current_turn"] >= state["max_turns"]:
        state["next_step"] = "evaluate_single_game"
    else:
        state["next_step"] = "simulate_turn"
    return state

def evaluate_single_game(state: GameSimState) -> GameSimState:
    print("📝 단일 게임 결과 평가 중...")
    prompt = ChatPromptTemplate.from_template("""
        당신은 수석 게임 밸런스 분석가입니다.
        아래 **5가지 밸런스 평가 기준**과 게임 시뮬레이션 로그를 바탕으로, 날카로운 분석 리포트를 작성해주세요.
        승리 플레이어와 점수는 시뮬레이션 로그를 기반으로 임의로 생성해도 좋습니다.

        [밸런스 평가 기준]
        1. **역할/시작 조건 밸런스:** 각 플레이어가 선택한 역할(캐릭터, 종족 등)이나 시작 조건이 승리에 동등한 기회를 제공하는가? 특정 역할이 너무 강력하거나 약하지 않은가?
        2. **전략 다양성:** 승리로 가는 길이 단 하나뿐인가, 아니면 다양한 전략이 유효한가?
        3. **자원 경제:** 핵심 자원의 획득과 소모가 균형 있고, 자원 관리가 전략적으로 중요한가?
        4. **게임 진행 속도(Pacing):** 게임이 너무 빠르거나 지루하게 늘어지지 않는가? 초반/중반/후반의 경험이 뚜렷하게 구분되는가?
        5. **운 요소 영향력:** 주사위나 카드 뽑기 같은 무작위성이 실력보다 승패에 더 큰 영향을 미치는가?

        # 시뮬레이션 로그
        {log}

        ---
        [분석 리포트 작성]
        게임 요약 및 승패 분석 (JSON 형식)
        ```json
        {{
            "winner": "승리 플레이어 (예: 플레이어 1 또는 역할 이름)",
            "totalTurns": [총 턴 수 (정수)],
            "durationMinutes": [예상 게임 시간 (분, 정수)],
            "score": {{ "Player 1": [점수], "Player 2": [점수], ... }},
            "keyStrategies": ["승패를 가른 결정적인 전략이나 플레이 1", "결정적인 전략이나 플레이 2"],
            "criticalMoments": ["게임 흐름을 바꾼 순간 1", "게임 흐름을 바꾼 순간 2"],
            "overallPacing": "게임의 전반적인 진행 속도 및 분위기 요약"
        }}
        ```
        상세 밸런스 평가 (항목별 구체적 평가)
        - **역할/시작 조건 밸런스:** (각 역할의 유불리, 특정 역할의 압도적 우위 여부 등을 구체적으로 평가)
        - **전략 다양성:** (다양한 승리 전략이 실제로 사용되었는지, 특정 전략만이 유효했는지 평가)
        - **자원 경제:** (자원 획득 및 소모의 균형, 특정 자원의 중요도, 자원 관리의 전략적 깊이 평가)
        - **게임 진행 속도(Pacing):** (게임이 너무 빠르거나 느리지는 않았는지, 플레이어들이 지루함을 느끼는 구간은 없었는지 평가)
        - **운 요소 영향력:** (운적인 요소가 승패에 미친 영향력을 평가. 실력과 운의 조화가 적절했는지 분석)
    """)
    chain = prompt | llm_default
    evaluation_raw_text = chain.invoke({"log": "\n\n".join(state["turn_log"])}).content
    state["single_game_evaluation"] = evaluation_raw_text
    state["all_evaluations_log"].append(evaluation_raw_text)
    print("   > 단일 게임 평가 완료.")
    state["next_step"] = "end_simulation"
    return state


# --- 그래프(Graph) 구성 (밸런스 테스트.ipynb에서 가져옴) ---
workflow = StateGraph(GameSimState)

workflow.add_node("start_new_game", start_new_game)
workflow.add_node("simulate_turn", simulate_turn)
workflow.add_node("evaluate_and_decide", evaluate_and_decide)
workflow.add_node("evaluate_single_game", evaluate_single_game)

workflow.add_edge(START, "start_new_game")
workflow.add_edge("start_new_game", "simulate_turn")
workflow.add_edge("simulate_turn", "evaluate_and_decide")
workflow.add_conditional_edges(
    "evaluate_and_decide",
    lambda state: state["next_step"],
    {"simulate_turn": "simulate_turn", "evaluate_single_game": "evaluate_single_game"},
)
workflow.add_edge("evaluate_single_game", END)

simulation_app = workflow.compile()


# -----------------------------------------------------------------------------
# 4. FastAPI 엔드포인트 정의
# -----------------------------------------------------------------------------

# 4-1. 컨셉 재생성 엔드포인트
class RegenerateConceptRequest(BaseModel):
    conceptId: int = Field(..., example=12, description="재생성할 원본 컨셉의 ID")
    planId: int = Field(..., example=13, description="재생성된 컨셉에 유지될 기획안 ID")
    feedback: str = Field(..., example="좀 더 캐주얼한 분위기였으면 좋겠어요.", description="컨셉 재생성을 위한 사용자 피드백")

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

@app.post("/api/plans/regenerate-concept", response_model=RegeneratedConceptResponse, summary="기존 보드게임 컨셉 재생성 (피드백 반영)")
async def regenerate_concept_api_endpoint(request: RegenerateConceptRequest):
    try:
        regenerated_concept = regenerate_board_game_concept_logic(request.dict())
        return regenerated_concept
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류 발생: {e}")


# 4-2. 게임 목표 생성 엔드포인트
class GameObjectiveRequest(BaseModel):
    conceptId: int = Field(..., example=12, description="게임 목표를 생성할 보드게임 컨셉의 ID")

class GameObjectiveResponse(BaseModel):
    mainGoal: str = Field(..., description="플레이어가 게임에서 궁극적으로 달성해야 할 주요 목표")
    subGoals: List[str] = Field(..., description="승리에 기여할 수 있는 보조 목표 목록")
    winConditionType: str = Field(..., description="승리 조건 유형 (예: 목표 달성형, 생존형, 점수 경쟁형 등)")
    designNote: str = Field(..., description="게임 목표 설계에 대한 간략한 디자이너 노트 또는 의도 설명")

@app.post("/generate-objective", response_model=GameObjectiveResponse, summary="게임 목표 생성")
async def generate_objective_api(request: GameObjectiveRequest):
    try:
        game_objective = generate_game_objective_logic(request.conceptId)
        return game_objective
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류 발생: {e}")


# 4-3. 구성요소 생성 엔드포인트
class ComponentItem(BaseModel):
    type: str
    name: str
    effect: str
    visualType: str # "2D" 또는 "3D"

class GenerateComponentsRequest(BaseModel):
    planId: int = Field(..., example=1012, description="구성요소를 생성할 기획안의 ID")

class GenerateComponentsResponse(BaseModel):
    components: List[ComponentItem]

@app.post("/generate-components", response_model=GenerateComponentsResponse, summary="컨셉/목표 기반 구성요소 생성")
async def generate_components_api(request: GenerateComponentsRequest):
    try:
        components_data = generate_game_components_logic(request.planId)
        return components_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류 발생: {e}")


# 4-4. 게임 규칙 생성 엔드포인트
class GenerateRulesRequest(BaseModel):
    conceptId: int = Field(..., example=12, description="게임 규칙을 생성할 컨셉의 ID")

class GenerateRulesResponse(BaseModel):
    ruleId: int
    turnStructure: str
    actionRules: List[str]
    victoryCondition: str
    penaltyRules: List[str]
    designNote: str

@app.post("/generate-rules", response_model=GenerateRulesResponse, summary="컨셉/목표 기반 게임 규칙 생성")
async def generate_rules_api(request: GenerateRulesRequest):
    try:
        game_rules_data = generate_game_rules_logic(request.conceptId)
        return game_rules_data
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류 발생: {e}")


# 4-5. 게임 규칙 재생성 엔드포인트
class RegenerateRulesRequest(BaseModel):
    ruleId: int = Field(..., example=23, description="재생성할 원본 규칙의 ID")
    feedback: str = Field(..., example="행동이 너무 단순한 것 같아요. 좀 더 다양한 전략이 있었으면 해요.", description="규칙 재생성을 위한 사용자 피드백")

class RegeneratedRulesResponse(BaseModel):
    ruleId: int
    turnStructure: str
    actionRules: List[str]
    victoryCondition: str
    penaltyRules: List[str]
    designNote: str

@app.post("/api/plans/regenerate-rule", response_model=RegeneratedRulesResponse, summary="게임 규칙 재생성 (피드백 반영)")
async def regenerate_rules_api_endpoint(request: RegenerateRulesRequest):
    try:
        regenerated_rules = regenerate_game_rules_logic(request.dict())
        return regenerated_rules
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류 발생: {e}")


# 4-6. 게임 규칙 시뮬레이션 엔드포인트 (✨ 최종 수정된 부분)
class SimulateRulesRequest(BaseModel):
    ruleId: int = Field(..., example=3105, description="시뮬레이션할 규칙의 ID")
    simulationCount: int = Field(..., example=3, description="수행할 시뮬레이션 게임의 수", ge=1, le=10)
    playerCount: int = Field(..., example=2, description="각 게임의 플레이어 수", ge=2, le=4)
    maxTurns: int = Field(..., example=10, description="게임당 최대 턴 수", ge=5, le=20)

class SimulationResultItem(BaseModel):
    gameId: int
    turns_log: List[str]
    winner: str
    totalTurns: int
    durationMinutes: int
    score: Dict[str, int]
    keyStrategies: List[str]
    criticalMoments: List[str]
    overallPacing: str
    balanceEvaluation: str

class BalanceAnalysis(BaseModel):
    simulationSummary: str = Field(..., description="시뮬레이션 요약")
    issuesDetected: List[str] = Field(..., description="발견된 문제점 목록")
    recommendations: List[str] = Field(..., description="개선 제안 목록")
    balanceScore: float = Field(..., ge=1.0, le=10.0, description="종합 밸런스 점수 (1.0~10.0)")

class SimulateRulesResponse(BaseModel):
    simulationHistory: List[SimulationResultItem]
    balanceAnalysis: BalanceAnalysis


@app.post("/api/simulate/rule-test", response_model=SimulateRulesResponse, summary="게임 규칙 시뮬레이션 및 밸런스 분석 실행")
async def simulate_rules_api(request: SimulateRulesRequest):
    rule_id_to_simulate = request.ruleId
    simulation_count = request.simulationCount
    player_count = request.playerCount
    max_turns = request.maxTurns

    rule_data = game_rules_database.get(rule_id_to_simulate)
    if not rule_data:
        raise HTTPException(status_code=404, detail=f"Rule ID {rule_id_to_simulate}에 해당하는 규칙 데이터를 찾을 수 없습니다.")

    game_rules_text_for_sim = rule_data.get("full_rule_text_for_llm")
    if not game_rules_text_for_sim:
        raise HTTPException(
            status_code=400,
            detail=f"Rule ID {rule_id_to_simulate}에 해당하는 'full_rule_text_for_llm'이 없습니다. 상세 규칙 텍스트를 추가해주세요."
        )

    try:
        initial_state = {
            "game_rules_text": game_rules_text_for_sim,
            "max_turns": max_turns,
            "all_evaluations_log": [],
            "player_count_override": player_count
        }
        analyzed_state = analyze_game_rules(initial_state)
        base_state_for_sim = generate_simulation_strategy(analyzed_state)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"초기 게임 분석 또는 전략 수립 중 오류 발생: {e}")

    all_simulation_results = []
    all_eval_logs = []

    for i in range(simulation_count):
        print(f"--- 🎲 {i + 1}번째 게임 시뮬레이션 시작 🎲 ---")
        current_game_state_copy = base_state_for_sim.copy()
        current_game_state_copy["all_evaluations_log"] = []
        current_game_state_copy["player_count_override"] = player_count
        current_game_state_copy["max_turns"] = max_turns

        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        try:
            final_sim_state = simulation_app.invoke(
                current_game_state_copy,
                {"recursion_limit": 50}
            )
        except Exception as e:
            print(f"개별 시뮬레이션 ({i+1}번째) 실행 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            final_sim_state = {}
        finally:
            sys.stdout = old_stdout
            simulation_console_log = redirected_output.getvalue()
            print(simulation_console_log)


        if final_sim_state and final_sim_state.get("single_game_evaluation"):
            evaluation_text = final_sim_state["single_game_evaluation"]
            all_eval_logs.append(evaluation_text)

            json_match_eval = re.search(r"```json\s*(\{.*?\})\s*```", evaluation_text, re.DOTALL)
            parsed_eval_json = {}
            if json_match_eval:
                try:
                    parsed_eval_json = json.loads(json_match_eval.group(1))
                except json.JSONDecodeError as e:
                    print(f"경고: 단일 게임 평가 JSON 파싱 오류: {e}")

            sim_result = SimulationResultItem(
                gameId=i + 1,
                turns_log=final_sim_state.get("turn_log", []),
                winner=parsed_eval_json.get("winner", "알 수 없음"),
                totalTurns=parsed_eval_json.get("totalTurns", final_sim_state.get("current_turn", 0)),
                durationMinutes=parsed_eval_json.get("durationMinutes", random.randint(30, 90)),
                score=parsed_eval_json.get("score", {}),
                keyStrategies=parsed_eval_json.get("keyStrategies", []),
                criticalMoments=parsed_eval_json.get("criticalMoments", []),
                overallPacing=parsed_eval_json.get("overallPacing", "평가 없음"),
                balanceEvaluation=evaluation_text.replace(json_match_eval.group(0), "").strip() if json_match_eval else evaluation_text
            )
            all_simulation_results.append(sim_result)
        else:
            all_simulation_results.append(SimulationResultItem(
                gameId=i + 1, turns_log=["시뮬레이션 실패 또는 불완전"], winner="N/A",
                totalTurns=0, durationMinutes=0, score={}, keyStrategies=[], criticalMoments=[],
                overallPacing="N/A", balanceEvaluation="평가 실패"
            ))

    final_report_prompt = ChatPromptTemplate.from_template("""
        당신은 수석 보드게임 밸런스 분석가입니다. 게임의 기본 정보와 여러 시뮬레이션 평가 결과를 종합하여,
        게임의 잠재적 문제점을 진단하고 구체적인 개선안을 제시하는 최종 보고서를 작성해주세요.

        1. 게임 기본 정보
        {summary}

        2. 개별 시뮬레이션 평가 로그
        {eval_logs}
        ---
        **[최종 보고서 작성 지침]**
        1. 분석 개요
        (게임의 핵심 컨셉과 특징, 이번 밸런스 테스트의 주요 목적을 1~2문단으로 서술하세요.)

        2. 종합 밸런스 평가
        (모든 시뮬레이션 결과를 바탕으로, 5가지 밸런스 평가 항목(역할, 전략, 자원, 속도, 운)에 대해 심층적으로 분석해주세요. 각 항목별로 평균적인 점수를 매기고, 왜 그렇게 평가했는지 구체적인 사례를 들어 설명해야 합니다.)

        3. 발견된 핵심 문제점
        (모든 분석을 종합했을 때, 이 게임의 밸런스에 가장 큰 영향을 미치는 문제점 1~2가지를 명확히 정의하고, 이 문제점이 게임의 재미를 어떻게 해치는지 설명해주세요.)

        4. 규칙 개선 제안
        (위에서 정의한 핵심 문제점을 해결하기 위한 구체적인 규칙 수정안을 2~3가지 제시해주세요. 단순히 '수정해야 한다'가 아니라, 'A 규칙을 B처럼 변경하여 C 효과를 기대할 수 있다'와 같이 상세하게 제안해야 합니다.)
    """)
    final_report_chain = final_report_prompt | llm_default
    try:
        final_balance_report_text = final_report_chain.invoke({
            "summary": base_state_for_sim.get("game_summary", ""),
            "eval_logs": "\n\n---\n\n".join(all_eval_logs)
        }).content
    except Exception as e:
        print(f"최종 보고서 생성 중 오류 발생: {e}")
        final_balance_report_text = f"최종 밸런스 보고서 생성에 실패했습니다: {e}"

    parser = JsonOutputParser(pydantic_object=BalanceAnalysis)
    parsing_prompt = ChatPromptTemplate.from_template(
        template="""
        당신은 분석 보고서 텍스트를 JSON 형식으로 변환하는 전문가입니다.
        아래 주어진 최종 밸런스 보고서 텍스트를 읽고, 요청된 JSON 형식에 맞춰 내용을 추출하고 요약해주세요.
        'balanceScore'는 보고서의 전반적인 긍정/부정 뉘앙스를 분석하여 1.0(매우 나쁨)에서 10.0(완벽함) 사이의 점수로 변환해주세요.
        
        {format_instructions}
        
        ---
        [분석 보고서 텍스트]
        {report_text}
        ---
        """,
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    parsing_chain = parsing_prompt | llm_default | parser

    try:
        parsed_balance_analysis = parsing_chain.invoke({"report_text": final_balance_report_text})
    except Exception as e:
        print(f"최종 보고서 파싱 실패: {e}")
        parsed_balance_analysis = BalanceAnalysis(
            simulationSummary="분석 보고서 요약에 실패했습니다.",
            issuesDetected=["보고서 분석 중 오류 발생"],
            recommendations=["LLM의 텍스트 출력을 확인해주세요."],
            balanceScore=5.0
        )

    return SimulateRulesResponse(
        simulationHistory=all_simulation_results,
        balanceAnalysis=parsed_balance_analysis
    )
