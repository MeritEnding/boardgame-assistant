import React, { useState } from 'react';

// --- 스타일링을 위한 Tailwind CSS 클래스 ---
// 이 코드는 create-react-app과 Tailwind CSS가 설정된 환경에서 작동합니다.
// 설정 방법: https://tailwindcss.com/docs/guides/create-react-app

const cardContainerStyle = "bg-white shadow-2xl rounded-2xl p-8 max-w-2xl w-full mx-auto my-10 transition-all duration-300 ease-in-out";
const inputStyle = "w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-shadow";
const buttonStyle = "w-full bg-indigo-600 text-white font-bold py-3 px-4 rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-transform transform hover:scale-105 disabled:bg-gray-400 disabled:cursor-not-allowed";
const resultSectionStyle = "mt-8 p-6 bg-gray-50 rounded-lg border border-gray-200 animate-fade-in";
const resultTitleStyle = "text-lg font-bold text-gray-800 mb-2";
const resultTextStyle = "text-gray-600 leading-relaxed";
const subGoalListStyle = "list-disc list-inside pl-4 mt-2";

// --- 컴포넌트 ---

function App() {
    const [conceptId, setConceptId] = useState('');
    const [gameObjective, setGameObjective] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!conceptId) {
            setError('컨셉 ID를 입력해주세요.');
            return;
        }

        setLoading(true);
        setError('');
        setGameObjective(null);

        try {
            // Spring Boot 백엔드 API 엔드포인트 호출
            const response = await fetch('http://localhost:8080/api/plans/generate-goal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ conceptId: parseInt(conceptId, 10) }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP Error: ${response.status}`);
            }

            const data = await response.json();
            setGameObjective(data);

        } catch (err) {
            setError(err.message || '데이터를 불러오는 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-gray-100 min-h-screen flex items-center justify-center font-sans p-4">
            <div className={cardContainerStyle}>
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-extrabold text-gray-900">보드게임 목표 생성기</h1>
                    <p className="text-gray-500 mt-2">컨셉 ID를 입력하여 AI가 생성하는 게임 목표를 확인하세요.</p>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <label htmlFor="conceptId" className="block text-sm font-medium text-gray-700 mb-2">
                            컨셉 ID (e.g., 1001, 1002, 12)
                        </label>
                        <input
                            id="conceptId"
                            type="number"
                            value={conceptId}
                            onChange={(e) => setConceptId(e.target.value)}
                            placeholder="컨셉 ID를 입력하세요..."
                            className={inputStyle}
                        />
                    </div>
                    <button type="submit" disabled={loading} className={buttonStyle}>
                        {loading ? '생성 중...' : '게임 목표 생성'}
                    </button>
                </form>

                {error && (
                    <div className="mt-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg animate-fade-in">
                        <strong>오류:</strong> {error}
                    </div>
                )}

                {gameObjective && (
                    <div className={resultSectionStyle}>
                        <div className="mb-6">
                            <h2 className={resultTitleStyle}>🎯 주요 목표 (Main Goal)</h2>
                            <p className={resultTextStyle}>{gameObjective.mainGoal}</p>
                        </div>

                        <div className="mb-6">
                            <h2 className={resultTitleStyle}>📜 보조 목표 (Sub Goals)</h2>
                            <ul className={subGoalListStyle}>
                                {gameObjective.subGoals.map((goal, index) => (
                                    <li key={index} className={resultTextStyle}>{goal}</li>
                                ))}
                            </ul>
                        </div>

                        <div className="mb-6">
                            <h2 className={resultTitleStyle}>🏆 승리 조건 유형 (Win Condition)</h2>
                            <p className={resultTextStyle}>{gameObjective.winConditionType}</p>
                        </div>

                        <div>
                            <h2 className={resultTitleStyle}>✍️ 디자이너 노트 (Design Note)</h2>
                            <p className={resultTextStyle}>{gameObjective.designNote}</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default App;
