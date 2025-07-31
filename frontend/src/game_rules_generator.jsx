import React, { useState } from 'react';
import axios from 'axios';


function GameRulePage() {
  const [conceptId, setConceptId] = useState('12');
  const [rules, setRules] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerateClick = async () => {
    if (!conceptId) {
      setError('컨셉 ID를 입력해주세요.');
      return;
    }
    setLoading(true);
    setRules(null);
    setError('');

    try {
      // 분리된 스프링 부트의 규칙 생성 API 호출
      const response = await axios.post('http://localhost:8080/api/plans/generate-rule', {
        conceptId: parseInt(conceptId, 10),
      });
      setRules(response.data);
    } catch (err) {
      const message = err.response ? `${err.response.status}: ${err.response.data}` : err.message;
      setError(`오류가 발생했습니다: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rule-page-container">
      <header>
        <h1>📖 AI 게임 규칙 생성기</h1>
        <p>게임 컨셉 ID를 기반으로 상세한 룰북을 생성합니다.</p>
      </header>
      
      <main>
        <div className="rule-input-section">
          <input
            type="number"
            value={conceptId}
            onChange={(e) => setConceptId(e.target.value)}
            placeholder="컨셉 ID (예: 1001, 12)"
          />
          <button onClick={handleGenerateClick} disabled={loading}>
            {loading ? '생성 중...' : '게임 규칙 생성'}
          </button>
        </div>

        {error && <p className="error-message">{error}</p>}

        {rules && (
          <div className="results">
            <h2>룰북 📖 생성된 게임 규칙</h2>
            <div className="result-card">
              <h3>⏳ 턴 구조</h3>
              <p>{rules.turnStructure}</p>
            </div>
            <div className="result-card">
              <h3>🎬 행동 규칙</h3>
              <ul>
                {rules.actionRules.map((rule, index) => (
                  <li key={index}>{rule}</li>
                ))}
              </ul>
            </div>
            <div className="result-card">
              <h3>🏆 승리 조건</h3>
              <p>{rules.victoryCondition}</p>
            </div>
            <div className="result-card">
              <h3>⚠️ 페널티 규칙</h3>
              <ul>
                {rules.penaltyRules.map((rule, index) => (
                  <li key={index}>{rule}</li>
                ))}
              </ul>
            </div>
            <div className="result-card">
              <h3>📝 디자이너 노트</h3>
              <p>{rules.designNote}</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default GameRulePage;
