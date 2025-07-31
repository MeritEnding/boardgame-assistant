import React, { useState } from 'react';
import axios from 'axios';

const ComponentGenerator = () => {
    // planId의 기본값으로 FastAPI 코드에 있는 1012를 설정
    const [planId, setPlanId] = useState(1012); 
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleGenerate = async () => {
        setLoading(true);
        setError('');
        setResult(null);

        try {
            // Spring Boot 컨트롤러에 정의한 API 주소로 요청
            const response = await axios.post(
                'http://localhost:8080/api/plans/generate-components', 
                { planId }
            );
            setResult(response.data);
        } catch (err) {
            setError('구성요소 생성 중 오류가 발생했습니다. 서버 상태를 확인해주세요.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
            <h1>🎲 보드게임 구성요소 생성</h1>
            <p>게임 기획안 ID(Plan ID)를 입력하고 버튼을 누르면, AI가 핵심 구성요소를 생성합니다.</p>
            
            <div style={{ marginBottom: '15px' }}>
                <label htmlFor="planId" style={{ marginRight: '10px' }}>Plan ID:</label>
                <input
                    id="planId"
                    type="number"
                    value={planId}
                    onChange={(e) => setPlanId(Number(e.target.value))}
                    placeholder="기획안 ID 입력 (예: 1012)"
                    style={{ padding: '8px', fontSize: '16px' }}
                />
            </div>

            <button 
                onClick={handleGenerate} 
                disabled={loading}
                style={{ padding: '10px 20px', fontSize: '16px', cursor: 'pointer' }}
            >
                {loading ? '생성 중...' : '구성요소 생성하기'}
            </button>

            {error && <p style={{ color: 'red', marginTop: '15px' }}>{error}</p>}

            {result && (
                <div style={{ marginTop: '20px', padding: '15px', border: '1px solid #ccc', borderRadius: '5px', background: '#f9f9f9' }}>
                    <h2>생성 결과 (Component ID: {result.componentId})</h2>
                    <ul style={{ listStyleType: 'none', paddingLeft: 0 }}>
                        {result.components.map((item, index) => (
                            <li key={index} style={{ borderBottom: '1px solid #eee', paddingBottom: '10px', marginBottom: '10px' }}>
                                <strong style={{ fontSize: '1.1em' }}>{item.name} ({item.type})</strong> - [{item.visualType}]
                                <p style={{ margin: '5px 0 0', color: '#555' }}>{item.effect}</p>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

export default ComponentGenerator;
