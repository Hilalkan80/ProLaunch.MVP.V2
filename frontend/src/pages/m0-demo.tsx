import { useState } from 'react';
import Head from 'next/head';
import { M0Container } from '../components/m0';

export default function M0Demo() {
  const [upgradeCalled, setUpgradeCalled] = useState(false);
  const [nextStepCalled, setNextStepCalled] = useState<string | null>(null);

  const handleUpgrade = () => {
    setUpgradeCalled(true);
    alert('Upgrade flow would be initiated here');
    setTimeout(() => setUpgradeCalled(false), 2000);
  };

  const handleStartNextStep = (stepId: string) => {
    setNextStepCalled(stepId);
    alert(`Starting step: ${stepId}`);
    setTimeout(() => setNextStepCalled(null), 2000);
  };

  const handleAnalysisComplete = (data: any) => {
    console.log('Analysis completed:', data);
  };

  return (
    <>
      <Head>
        <title>M0 Feasibility Analysis - ProLaunch.AI</title>
        <meta name="description" content="AI-powered product feasibility analysis" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="min-h-screen">
        {/* Status indicators for demo */}
        {(upgradeCalled || nextStepCalled) && (
          <div className="fixed top-4 right-4 z-50 bg-blue-100 border border-blue-300 rounded-lg p-3 shadow-lg">
            {upgradeCalled && (
              <p className="text-blue-800 text-sm">✅ Upgrade flow initiated</p>
            )}
            {nextStepCalled && (
              <p className="text-blue-800 text-sm">✅ Next step: {nextStepCalled}</p>
            )}
          </div>
        )}

        <M0Container
          onUpgrade={handleUpgrade}
          onStartNextStep={handleStartNextStep}
          onAnalysisComplete={handleAnalysisComplete}
        />
      </main>
    </>
  );
}