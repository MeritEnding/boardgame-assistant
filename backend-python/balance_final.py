import React, { useState } from 'react';
import axios from 'axios';


function SimulationPage() {
    // --- State ---
    const [playerNames, setPlayerNames] = useState('탐험가 A, 공학자 B');
    const [maxTurns, setMaxTurns] = useState(10);
    const [enablePenalty, setEnablePenalty] = useState(true);
    const [simulationResult, setSimulationResult] = useState(null);
    const [balanceFeedback, setBalanceFeedback] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const clearResults = () => {
        setSimulationResult(null);
        setBalanceFeedback(null);
        setError('');
    };

    // --- Handlers ---
    const handleRunSimulation = async () => {
        setLoading(true);
        clearResults();
        try {
            const names = playerNames.split(',').map(name => name.trim()).filter(name => name);
            const response = await axios.post('http://localhost:8080/api/simulate/rule-test', {
                ruleId: 101, // Rule ID is fixed to 101 for this example
                playerNames: names,
                maxTurns: parseInt(maxTurns, 10),
                enablePenalty,
            });
            setSimulationResult(response.data);
        } catch (err) {
            const message = err.response ? `${err.response.status}: ${err.response.data}` : err.message;
            setError(`시뮬레이션 오류: ${message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleGetBalance = async () => {
        setLoading(true);
        clearResults();
        try {
            const response = await axios.get('http://localhost:8080/api/feedback/balance');
            setBalanceFeedback(response.data);
        } catch (err) {
            const message = err.response ? `${err.response.status}: ${err.response.data}` : err.message;
            setError(`밸런스 분석 오류: ${message}`);
        } finally {
            setLoading(false);
        }
    };

    // --- Render ---
    return (
        <div className="sim-container">
            <header>
                <h1>🕹️ 게임 시뮬레이션 및 밸런스 분석</h1>
                <p>가상 플레이 로그를 생성하고 LLM 기반 밸런스 피드백을 확인합니다.</p>
            </header>

            <div className="sim-controls">
                <div className="control-group">
                    <label>플레이어 이름 (쉼표로 구분)</label>
                    <input type="text" value={playerNames} onChange={e => setPlayerNames(e.target.value)} />
                </div>
                <div className="control-group">
                    <label>최대 턴 수</label>
                    <input type="number" value={maxTurns} onChange={e => setMaxTurns(e.target.value)} />
                </div>
                <div className="control-group checkbox">
                    <input type="checkbox" id="penalty" checked={enablePenalty} onChange={e => setEnablePenalty(e.target.checked)} />
                    <label htmlFor="penalty">페널티 규칙 적용</label>
                </div>
                <div className="button-group">
                    <button onClick={handleRunSimulation} disabled={loading}>{loading ? '실행 중...' : '시뮬레이션 실행'}</button>
                    <button onClick={handleGetBalance} disabled={loading}>{loading ? '분석 중...' : '밸런스 분석 보기'}</button>
                </div>
            </div>
            
            {error && <p className="error-message">{error}</p>}

            {simulationResult && <SimulationResultDisplay result={simulationResult} />}
            {balanceFeedback && <BalanceFeedbackDisplay feedback={balanceFeedback} />}
        </div>
    );
}

// --- 결과 표시 컴포넌트 ---
const SimulationResultDisplay = ({ result }) => (
    <div className="results-panel">
        <h2>📊 시뮬레이션 결과</h2>
        {result.simulationHistory.map(game => (
            <div key={game.gameId} className="game-log">
                <h3>게임 요약</h3>
                <p><strong>승자:</strong> {game.winner}</p>
                <p><strong>총 턴 수:</strong> {game.totalTurns} ({game.durationMinutes}분 소요)</p>
                <p><strong>승리 조건:</strong> {game.victoryCondition}</p>
                <div className="turn-logs">
                    {game.turns.map(turn => (
                        <details key={turn.turn} className="turn-details">
                            <summary><strong>턴 {turn.turn}</strong></summary>
                            <ul>
                                {turn.actions.map((action, index) => (
                                    <li key={index}>
                                        <strong>{action.player}의 행동: {action.action}</strong>
                                        <p>세부사항: {action.details}</p>
                                        <p><em>선택 이유: {action.rationale}</em></p>
                                    </li>
                                ))}
                            </ul>
                        </details>
                    ))}
                </div>
            </div>
        ))}
    </div>
);

const BalanceFeedbackDisplay = ({ feedback }) => {
    const { balanceAnalysis } = feedback;
    const scoreColor = balanceAnalysis.balanceScore >= 8 ? 'green' : balanceAnalysis.balanceScore >= 6 ? 'orange' : 'red';
    return (
        <div className="results-panel">
            <h2>⚖️ 밸런스 분석 피드백</h2>
            <div className="feedback-card">
                <h3>종합 평점: <span style={{ color: scoreColor }}>{balanceAnalysis.balanceScore} / 10.0</span></h3>
                <p><strong>요약:</strong> {balanceAnalysis.simulationSummary}</p>
            </div>
            <div className="feedback-card">
                <h3>감지된 문제점</h3>
                <ul>{balanceAnalysis.issuesDetected.map((issue, i) => <li key={i}>{issue}</li>)}</ul>
            </div>
            <div className="feedback-card">
                <h3>개선 권장 사항</h3>
                <ul>{balanceAnalysis.recommendations.map((rec, i) => <li key={i}>{rec}</li>)}</ul>
            </div>
        </div>
    );
};

export default SimulationPage;
