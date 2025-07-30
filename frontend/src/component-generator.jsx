import React, { useState } from 'react';
import axios from 'axios';
import './App.css'; // 간단한 스타일링을 위해 CSS 파일 임포트

function App() {
  // 폼 데이터를 관리하는 상태
  const [formData, setFormData] = useState({
    theme: '우주 탐사',
    playerCount: '2~4명',
    averageWeight: 2.5,
  });

  // API 호출 결과를 저장하는 상태
  const [result, setResult] = useState(null);
  // 로딩 상태를 관리하는 상태
  const [loading, setLoading] = useState(false);
  // 에러 상태를 관리하는 상태
  const [error, setError] = useState('');

  // 입력 필드 값이 변경될 때마다 formData 상태를 업데이트
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'averageWeight' ? parseFloat(value) : value,
    }));
  };

  // 폼 제출 시 실행될 함수
  const handleSubmit = async (e) => {
    e.preventDefault(); // 폼 기본 제출 동작 방지
    setLoading(true);
    setError('');
    setResult(null);

    try {
      // Spring Boot 서버에 POST 요청
      const response = await axios.post(
        'http://localhost:8080/api/v1/concepts/generate',
        formData
      );
      setResult(response.data); // 성공 시 결과 저장
    } catch (err) {
      setError('컨셉 생성에 실패했습니다. 잠시 후 다시 시도해주세요.');
      console.error(err);
    } finally {
      setLoading(false); // 로딩 종료
    }
  };

  return (
    <div className="container">
      <header>
        <h1>🤖 보드게임 컨셉 생성기</h1>
        <p>AI가 세상에 없던 새로운 보드게임 아이디어를 제안해 드립니다.</p>
      </header>

      <form onSubmit={handleSubmit} className="concept-form">
        <div className="form-group">
          <label htmlFor="theme">테마</label>
          <input
            type="text"
            id="theme"
            name="theme"
            value={formData.theme}
            onChange={handleChange}
            placeholder="예: 판타지, 중세, 경제"
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="playerCount">플레이 인원</label>
          <input
            type="text"
            id="playerCount"
            name="playerCount"
            value={formData.playerCount}
            onChange={handleChange}
            placeholder="예: 2~4명, 3명"
            required
          />
        </div>
        <div className="form-group">
          <label htmlFor="averageWeight">난이도: {formData.averageWeight.toFixed(1)}</label>
          <input
            type="range"
            id="averageWeight"
            name="averageWeight"
            min="1.0"
            max="5.0"
            step="0.1"
            value={formData.averageWeight}
            onChange={handleChange}
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? '생성 중...' : '컨셉 생성하기'}
        </button>
      </form>

      {error && <div className="error-message">{error}</div>}

      {result && (
        <div className="result-card">
          <h2>✨ 생성된 컨셉: {result.theme}</h2>
          <div className="result-grid">
            <p><strong>👥 추천 인원:</strong> {result.playerCount}</p>
            <p><strong>⚖️ 예상 난이도:</strong> {result.averageWeight}</p>
            <p><strong>🗓️ 생성일:</strong> {new Date(result.createdAt).toLocaleString()}</p>
          </div>
          <div className="result-section">
            <h3>📖 스토리라인</h3>
            <p>{result.storyline}</p>
          </div>
          <div className="result-section">
            <h3>🎯 핵심 아이디어</h3>
            <p>{result.ideaText}</p>
          </div>
          <div className="result-section">
            <h3>⚙️ 주요 메커니즘</h3>
            <p>{result.mechanics}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
