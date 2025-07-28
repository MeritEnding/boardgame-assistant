import React, { useState } from 'react';
import './App.css'; // 기본 CSS 파일 사용

function App() {
  const [theme, setTheme] = useState('');
  const [playerCount, setPlayerCount] = useState('');
  const [averageWeight, setAverageWeight] = useState(2.0);
  const [concept, setConcept] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setConcept(null); // 이전 결과 초기화

    try {
      const response = await fetch('http://localhost:8080/generate-concept', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          theme,
          playerCount,
          averageWeight: parseFloat(averageWeight),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '컨셉 생성에 실패했습니다.');
      }

      const data = await response.json();
      setConcept(data);
    } catch (err) {
      console.error("API 호출 오류:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>보드게임 컨셉 생성기</h1>
      </header>
      <main>
        <form onSubmit={handleSubmit} className="concept-form">
          <div className="form-group">
            <label htmlFor="theme">테마:</label>
            <input
              type="text"
              id="theme"
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              placeholder="예: 중세 판타지, SF 우주, 현대 도시"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="playerCount">플레이 인원수:</label>
            <input
              type="text"
              id="playerCount"
              value={playerCount}
              onChange={(e) => setPlayerCount(e.target.value)}
              placeholder="예: 2~4명, 3명, 5명"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="averageWeight">난이도 (1.0~5.0):</label>
            <input
              type="number"
              id="averageWeight"
              value={averageWeight}
              onChange={(e) => setAverageWeight(e.target.value)}
              min="1.0"
              max="5.0"
              step="0.1"
              required
            />
          </div>
          <button type="submit" disabled={loading}>
            {loading ? '컨셉 생성 중...' : '컨셉 생성하기'}
          </button>
        </form>

        {error && <p className="error-message">오류: {error}</p>}

        {concept && (
          <div className="concept-result">
            <h2>새로운 보드게임 컨셉:</h2>
            <p><strong>컨셉 ID:</strong> {concept.conceptId}</p>
            <p><strong>계획 ID:</strong> {concept.planId}</p>
            <p><strong>테마:</strong> {concept.theme}</p>
            <p><strong>플레이 인원수:</strong> {concept.playerCount}</p>
            <p><strong>난이도:</strong> {concept.averageWeight.toFixed(1)}</p>
            <h3>핵심 아이디어:</h3>
            <p>{concept.ideaText}</p>
            <h3>주요 메커니즘:</h3>
            <p>{concept.mechanics}</p>
            <h3>배경 스토리:</h3>
            <p>{concept.storyline}</p>
            <p className="created-at">생성 시간: {new Date(concept.createdAt).toLocaleString('ko-KR')}</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
