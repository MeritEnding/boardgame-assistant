import React, { useState } from 'react';
import './App.css'; // 기본 CSS 파일 사용

function App() {
  // 기존 컨셉 생성 상태
  const [theme, setTheme] = useState('');
  const [playerCount, setPlayerCount] = useState('');
  const [averageWeight, setAverageWeight] = useState(2.0);
  const [concept, setConcept] = useState(null);
  const [loadingConcept, setLoadingConcept] = useState(false);
  const [errorConcept, setErrorConcept] = useState(null);

  // 게임 목표 생성 상태
  const [objectiveConceptId, setObjectiveConceptId] = useState('');
  const [objective, setObjective] = useState(null);
  const [loadingObjective, setLoadingObjective] = useState(false);
  const [errorObjective, setErrorObjective] = useState(null);

  // 구성요소 생성 상태
  const [componentPlanId, setComponentPlanId] = useState('');
  const [components, setComponents] = useState(null);
  const [loadingComponents, setLoadingComponents] = useState(false);
  const [errorComponents, setErrorComponents] = useState(null);

  // 게임 규칙 생성 상태
  const [rulesConceptId, setRulesConceptId] = useState('');
  const [rules, setRules] = useState(null);
  const [loadingRules, setLoadingRules] = useState(false);
  const [errorRules, setErrorRules] = useState(null);

  // 새롭게 추가된 컨셉 재생성 상태
  const [regenerateConceptId, setRegenerateConceptId] = useState('');
  const [regeneratePlanId, setRegeneratePlanId] = useState('');
  const [regenerateFeedback, setRegenerateFeedback] = useState('');
  const [regeneratedConcept, setRegeneratedConcept] = useState(null);
  const [loadingRegenerate, setLoadingRegenerate] = useState(false);
  const [errorRegenerate, setErrorRegenerate] = useState(null);


  // 컨셉 생성 핸들러
  const handleGenerateConcept = async (e) => {
    e.preventDefault();
    setLoadingConcept(true);
    setErrorConcept(null);
    setConcept(null);

    try {
      const response = await fetch('http://localhost:8000/generate-concept', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme, playerCount, averageWeight: parseFloat(averageWeight) }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '컨셉 생성에 실패했습니다.');
      }
      const data = await response.json();
      setConcept(data);
    } catch (err) {
      console.error("컨셉 생성 API 호출 오류:", err);
      setErrorConcept(err.message);
    } finally {
      setLoadingConcept(false);
    }
  };

  // 게임 목표 생성 핸들러
  const handleGenerateObjective = async (e) => {
    e.preventDefault();
    setLoadingObjective(true);
    setErrorObjective(null);
    setObjective(null);

    try {
      const response = await fetch('http://localhost:8000/generate-objective', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conceptId: parseInt(objectiveConceptId) }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '게임 목표 생성에 실패했습니다.');
      }
      const data = await response.json();
      setObjective(data);
    } catch (err) {
      console.error("게임 목표 API 호출 오류:", err);
      setErrorObjective(err.message);
    } finally {
      setLoadingObjective(false);
    }
  };

  // 구성요소 생성 핸들러
  const handleGenerateComponents = async (e) => {
    e.preventDefault();
    setLoadingComponents(true);
    setErrorComponents(null);
    setComponents(null);

    try {
      const response = await fetch('http://localhost:8000/generate-components', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ planId: parseInt(componentPlanId) }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '구성요소 생성에 실패했습니다.');
      }
      const data = await response.json();
      setComponents(data.components); 
    } catch (err) {
      console.error("구성요소 API 호출 오류:", err);
      setErrorComponents(err.message);
    } finally {
      setLoadingComponents(false);
    }
  };

  // 게임 규칙 생성 핸들러
  const handleGenerateRules = async (e) => {
    e.preventDefault();
    setLoadingRules(true);
    setErrorRules(null);
    setRules(null);

    try {
      const response = await fetch('http://localhost:8000/generate-rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conceptId: parseInt(rulesConceptId) }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '게임 규칙 생성에 실패했습니다.');
      }
      const data = await response.json();
      setRules(data);
    } catch (err) {
      console.error("게임 규칙 API 호출 오류:", err);
      setErrorRules(err.message);
    } finally {
      setLoadingRules(false);
    }
  };

  // 새롭게 추가된 컨셉 재생성 핸들러
  const handleRegenerateConcept = async (e) => {
    e.preventDefault();
    setLoadingRegenerate(true);
    setErrorRegenerate(null);
    setRegeneratedConcept(null); // 이전 결과 초기화

    try {
      const response = await fetch('http://localhost:8000/api/plans/regenerate-concept', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conceptId: parseInt(regenerateConceptId),
          planId: parseInt(regeneratePlanId), // planId 포함
          feedback: regenerateFeedback,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '컨셉 재생성에 실패했습니다.');
      }

      const data = await response.json();
      setRegeneratedConcept(data);
    } catch (err) {
      console.error("컨셉 재생성 API 호출 오류:", err);
      setErrorRegenerate(err.message);
    } finally {
      setLoadingRegenerate(false);
    }
  };


  return (
    <div className="App">
      <header className="App-header">
        <h1>보드게임 기획 도구</h1>
      </header>
      <main>
        {/* --- 새로운 컨셉 생성 섹션 --- */}
        <section className="feature-section">
          <h2>새로운 보드게임 컨셉 생성</h2>
          <form onSubmit={handleGenerateConcept} className="concept-form">
            <div className="form-group">
              <label htmlFor="theme">테마:</label>
              <input type="text" id="theme" value={theme} onChange={(e) => setTheme(e.target.value)} placeholder="예: 중세 판타지, SF 우주" required />
            </div>
            <div className="form-group">
              <label htmlFor="playerCount">플레이 인원수:</label>
              <input type="text" id="playerCount" value={playerCount} onChange={(e) => setPlayerCount(e.target.value)} placeholder="예: 2~4명" required />
            </div>
            <div className="form-group">
              <label htmlFor="averageWeight">난이도 (1.0~5.0):</label>
              <input type="number" id="averageWeight" value={averageWeight} onChange={(e) => setAverageWeight(e.target.value)} min="1.0" max="5.0" step="0.1" required />
            </div>
            <button type="submit" disabled={loadingConcept}>
              {loadingConcept ? '컨셉 생성 중...' : '컨셉 생성하기'}
            </button>
          </form>
          {errorConcept && <p className="error-message">오류: {errorConcept}</p>}
          {concept && (
            <div className="concept-result">
              <h3>생성된 컨셉:</h3>
              <p><strong>컨셉 ID:</strong> {concept.conceptId}</p>
              <p><strong>계획 ID:</strong> {concept.planId}</p>
              <p><strong>테마:</strong> {concept.theme}</p>
              <p><strong>플레이 인원수:</strong> {concept.playerCount}</p>
              <p><strong>난이도:</strong> {concept.averageWeight.toFixed(1)}</p>
              <h4>핵심 아이디어:</h4><p>{concept.ideaText}</p>
              <h4>주요 메커니즘:</h4><p>{concept.mechanics}</p>
              <h4>배경 스토리:</h4><p>{concept.storyline}</p>
              <p className="created-at">생성 시간: {new Date(concept.createdAt).toLocaleString('ko-KR')}</p>
            </div>
          )}
        </section>

        <hr />

        {/* --- 컨셉 재생성 섹션 --- */}
        <section className="feature-section">
          <h2>기존 컨셉 재생성 (피드백 반영)</h2>
          <form onSubmit={handleRegenerateConcept} className="regenerate-form">
            <div className="form-group">
              <label htmlFor="regenerateConceptId">원본 컨셉 ID:</label>
              <input
                type="number"
                id="regenerateConceptId"
                value={regenerateConceptId}
                onChange={(e) => setRegenerateConceptId(e.target.value)}
                placeholder="예: 12, 1001"
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="regeneratePlanId">기획안 ID (유지):</label>
              <input
                type="number"
                id="regeneratePlanId"
                value={regeneratePlanId}
                onChange={(e) => setRegeneratePlanId(e.target.value)}
                placeholder="예: 13, 2001"
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="regenerateFeedback">피드백:</label>
              <textarea
                id="regenerateFeedback"
                value={regenerateFeedback}
                onChange={(e) => setRegenerateFeedback(e.target.value)}
                placeholder="예: 좀 더 캐주얼한 분위기였으면 좋겠어요."
                rows="3"
                required
              ></textarea>
            </div>
            <button type="submit" disabled={loadingRegenerate}>
              {loadingRegenerate ? '컨셉 재생성 중...' : '컨셉 재생성하기'}
            </button>
          </form>

          {errorRegenerate && <p className="error-message">오류: {errorRegenerate}</p>}

          {regeneratedConcept && (
            <div className="concept-result">
              <h3>재생성된 컨셉:</h3>
              <p><strong>컨셉 ID:</strong> {regeneratedConcept.conceptId}</p>
              <p><strong>계획 ID:</strong> {regeneratedConcept.planId}</p>
              <p><strong>테마:</strong> {regeneratedConcept.theme}</p>
              <p><strong>플레이 인원수:</strong> {regeneratedConcept.playerCount}</p>
              <p><strong>난이도:</strong> {regeneratedConcept.averageWeight.toFixed(1)}</p>
              <h4>핵심 아이디어:</h4><p>{regeneratedConcept.ideaText}</p>
              <h4>주요 메커니즘:</h4><p>{regeneratedConcept.mechanics}</p>
              <h4>배경 스토리:</h4><p>{regeneratedConcept.storyline}</p>
              <p className="created-at">생성 시간: {new Date(regeneratedConcept.createdAt).toLocaleString('ko-KR')}</p>
            </div>
          )}
        </section>

        <hr />

        {/* --- 게임 목표 생성 섹션 --- */}
        <section className="feature-section">
          <h2>기존 컨셉 기반 게임 목표 생성</h2>
          <form onSubmit={handleGenerateObjective} className="objective-form">
            <div className="form-group">
              <label htmlFor="objectiveConceptId">컨셉 ID:</label>
              <input type="number" id="objectiveConceptId" value={objectiveConceptId} onChange={(e) => setObjectiveConceptId(e.target.value)} placeholder="예: 1001 또는 12" required />
            </div>
            <button type="submit" disabled={loadingObjective}>
              {loadingObjective ? '게임 목표 생성 중...' : '게임 목표 생성하기'}
            </button>
          </form>
          {errorObjective && <p className="error-message">오류: {errorObjective}</p>}
          {objective && (
            <div className="objective-result">
              <h3>생성된 게임 목표:</h3>
              <p><strong>주요 목표:</strong> {objective.mainGoal}</p>
              <p><strong>보조 목표:</strong> {objective.subGoals.join(', ')}</p>
              <p><strong>승리 조건 유형:</strong> {objective.winConditionType}</p>
              <h4>디자이너 노트:</h4><p>{objective.designNote}</p>
            </div>
          )}
        </section>

        <hr />

        {/* --- 구성요소 생성 섹션 --- */}
        <section className="feature-section">
          <h2>기획안 기반 구성요소 생성</h2>
          <form onSubmit={handleGenerateComponents} className="components-form">
            <div className="form-group">
              <label htmlFor="componentPlanId">기획안 ID (Plan ID):</label>
              <input type="number" id="componentPlanId" value={componentPlanId} onChange={(e) => setComponentPlanId(e.target.value)} placeholder="예: 1012, 2001, 3001" required />
            </div>
            <button type="submit" disabled={loadingComponents}>
              {loadingComponents ? '구성요소 생성 중...' : '구성요소 생성하기'}
            </button>
          </form>
          {errorComponents && <p className="error-message">오류: {errorComponents}</p>}
          {components && components.length > 0 && (
            <div className="components-result">
              <h3>생성된 구성요소:</h3>
              <ul>
                {components.map((comp, index) => (
                  <li key={index}>
                    <strong>유형:</strong> {comp.type} | 
                    <strong> 이름:</strong> {comp.name} | 
                    <strong> 효과:</strong> {comp.effect} | 
                    <strong> 시각적 유형:</strong> {comp.visualType}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {components && components.length === 0 && !loadingComponents && !errorComponents && (
              <p>생성된 구성요소가 없습니다.</p>
          )}
        </section>

        <hr />

        {/* --- 게임 규칙 생성 섹션 --- */}
        <section className="feature-section">
          <h2>컨셉/목표 기반 게임 규칙 생성</h2>
          <form onSubmit={handleGenerateRules} className="rules-form">
            <div className="form-group">
              <label htmlFor="rulesConceptId">컨셉 ID:</label>
              <input type="number" id="rulesConceptId" value={rulesConceptId} onChange={(e) => setRulesConceptId(e.target.value)} placeholder="예: 12, 1001" required />
            </div>
            <button type="submit" disabled={loadingRules}>
              {loadingRules ? '게임 규칙 생성 중...' : '게임 규칙 생성하기'}
            </button>
          </form>
          {errorRules && <p className="error-message">오류: {errorRules}</p>}
          {rules && (
            <div className="rules-result">
              <h3>생성된 게임 규칙:</h3>
              <p><strong>규칙 ID:</strong> {rules.ruleId}</p>
              <p><strong>턴 구조:</strong> {rules.turnStructure}</p>
              <h4>행동 규칙:</h4>
              <ul>
                {rules.actionRules.map((rule, index) => (
                  <li key={index}>{rule}</li>
                ))}
              </ul>
              <p><strong>승리 조건:</strong> {rules.victoryCondition}</p>
              <h4>페널티 규칙:</h4>
              <ul>
                {rules.penaltyRules.map((penalty, index) => (
                  <li key={index}>{penalty}</li>
                ))}
              </ul>
              <h4>디자이너 노트:</h4>
              <p>{rules.designNote}</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
