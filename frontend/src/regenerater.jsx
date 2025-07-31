import React, { useState } from 'react';
import axios from 'axios';

// 각 섹션을 위한 범용 카드 컴포넌트
const SectionCard = ({ title, children }) => (
    <div className="regen-card">
        <h2>{title}</h2>
        {children}
    </div>
);

// --- 각 기능별 컴포넌트 ---

const ConceptRegenerator = () => {
    const [conceptId, setConceptId] = useState(12);
    const [planId, setPlanId] = useState(13);
    const [feedback, setFeedback] = useState('좀 더 캐주얼한 분위기였으면 좋겠어요.');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleRegenerate = async () => {
        setLoading(true);
        setResult(null);
        try {
            // (수정) API 경로 변경
            const response = await axios.post('http://localhost:8080/api/plans/regenerate-concept', 
                { conceptId, planId, feedback });
            setResult(response.data);
        } catch (error) { alert(`컨셉 재생성 오류: ${error.message}`); }
        setLoading(false);
    };

    return (
        <SectionCard title="컨셉 재생성">
            <div className="input-grid">
                <input type="number" value={conceptId} onChange={e => setConceptId(Number(e.target.value))} placeholder="Concept ID" />
                <input type="number" value={planId} onChange={e => setPlanId(Number(e.target.value))} placeholder="Plan ID" />
            </div>
            <textarea value={feedback} onChange={e => setFeedback(e.target.value)} placeholder="피드백을 입력하세요..." />
            <button onClick={handleRegenerate} disabled={loading}>{loading ? '생성중...' : '컨셉 재생성'}</button>
            {result && <div className="result-box"><pre>{JSON.stringify(result, null, 2)}</pre></div>}
        </SectionCard>
    );
};

const ComponentsRegenerator = () => {
    const [componentId, setComponentId] = useState(3543);
    const [feedback, setFeedback] = useState('토큰타입의 지형토큰이 아닌 다른 토큰도 추가해주세요!');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleRegenerate = async () => {
        setLoading(true);
        setResult(null);
        try {
            // (수정) API 경로 변경
            const response = await axios.post('http://localhost:8080/api/plans/regenerate-components', 
                { componentId, feedback });
            setResult(response.data);
        } catch (error) { alert(`구성요소 재생성 오류: ${error.message}`); }
        setLoading(false);
    };

    return (
        <SectionCard title="구성요소 재생성">
            <input type="number" value={componentId} onChange={e => setComponentId(Number(e.target.value))} placeholder="Component ID" />
            <textarea value={feedback} onChange={e => setFeedback(e.target.value)} placeholder="피드백을 입력하세요..." />
            <button onClick={handleRegenerate} disabled={loading}>{loading ? '생성중...' : '구성요소 재생성'}</button>
            {result && <div className="result-box"><pre>{JSON.stringify(result, null, 2)}</pre></div>}
        </SectionCard>
    );
};

const RuleRegenerator = () => {
    const [ruleId, setRuleId] = useState(23);
    const [feedback, setFeedback] = useState('행동이 너무 단순한 것 같아요. 좀 더 다양한 전략이 있었으면 해요.');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleRegenerate = async () => {
        setLoading(true);
        setResult(null);
        try {
            // (수정) API 경로 변경
            const response = await axios.post('http://localhost:8080/api/plans/regenerate-rule', 
                { ruleId, feedback });
            setResult(response.data);
        } catch (error) { alert(`규칙 재생성 오류: ${error.message}`); }
        setLoading(false);
    };
    
    return (
        <SectionCard title="규칙 재생성">
            <input type="number" value={ruleId} onChange={e => setRuleId(Number(e.target.value))} placeholder="Rule ID" />
            <textarea value={feedback} onChange={e => setFeedback(e.target.value)} placeholder="피드백을 입력하세요..." />
            <button onClick={handleRegenerate} disabled={loading}>{loading ? '생성중...' : '규칙 재생성'}</button>
            {result && <div className="result-box"><pre>{JSON.stringify(result, null, 2)}</pre></div>}
        </SectionCard>
    );
};


// --- 메인 페이지 컴포넌트 ---
function RegeneratePage() {
    return (
        <div className="regen-container">
            <h1>🎨 통합 재생성 페이지</h1>
            <p>피드백을 통해 게임의 컨셉, 구성요소, 규칙을 각각 개선합니다.</p>
            <div className="regen-grid">
                <ConceptRegenerator />
                <ComponentsRegenerator />
                <RuleRegenerator />
            </div>
        </div>
    );
}

export default RegeneratePage;
