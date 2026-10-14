import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { useSimulation } from '../context/SimulationContext';
import { SimulationConfigForm } from '../forms/SimulationConfigForm';
import { VariantRulesFormValues } from '../types/simulation';
import { Navbar } from '../components/Navbar';
import { Dices } from 'lucide-react';

export const ConfigurationPage: React.FC = () => {
  const navigate = useNavigate();
  const { createAndLaunchSimulation } = useSimulation();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (values: VariantRulesFormValues) => {
    setIsSubmitting(true);
    try {
      const response = await createAndLaunchSimulation(values);
      if (values.execution_mode === 'fast_batch') {
        navigate(`/batch/${response.session_id}`);
      } else {
        navigate(`/simulate/${response.session_id}`);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col bg-slate-950">
      <Navbar />
      {/* Container */}
      <div className="mx-auto w-full max-w-5xl px-4 py-8 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-5">
          <div className="space-y-1">
            <div className="flex items-center space-x-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <Dices className="h-6 w-6" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">
                Decision Blackjack Benchmark
              </h1>
            </div>
            <p className="text-sm text-slate-400">
              Deterministic casino benchmarking testbed comparing Jev (System One), Laya, and Basic Strategy.
            </p>
          </div>
        </div>

        {/* Configuration Form */}
        <SimulationConfigForm onSubmit={handleSubmit} isLoading={isSubmitting} />
      </div>
    </div>
  );
};
