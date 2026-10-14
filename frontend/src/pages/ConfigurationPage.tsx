import React, { useState } from "react";
import { useNavigate } from "react-router";
import { useSimulation } from "../context/SimulationContext";
import { SimulationConfigForm } from "../forms/SimulationConfigForm";
import { VariantRulesFormValues } from "../types/simulation";
import { Navbar } from "../components/Navbar";
import { Dices, Cpu, ShieldCheck, Zap } from "lucide-react";

export const ConfigurationPage: React.FC = () => {
  const navigate = useNavigate();
  const { createAndLaunchSimulation } = useSimulation();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (values: VariantRulesFormValues) => {
    setIsSubmitting(true);
    try {
      const response = await createAndLaunchSimulation(values);
      if (values.execution_mode === "fast_batch") {
        navigate(`/batch/${response.session_id}`);
      } else {
        navigate(`/simulate/${response.session_id}`);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col pb-16">
      <Navbar />

      {/* Main Container */}
      <div className="mx-auto w-full max-w-5xl px-4 py-8 space-y-8">
        {/* Hero Header */}
        <div className="relative rounded-2xl border border-[#2b305c] bg-gradient-to-r from-[#1e2353]/90 via-[#1e2353]/70 to-[#0a0d3a]/90 p-6 sm:p-8 shadow-2xl overflow-hidden">
          {/* Subtle decorative glow */}
          <div className="absolute -top-16 -right-16 h-48 w-48 rounded-full bg-[#ec48bd]/15 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-16 -left-16 h-48 w-48 rounded-full bg-[#5865f2]/20 blur-3xl pointer-events-none" />

          <div className="relative z-10 space-y-4">
            <div className="flex items-center space-x-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-sm bg-[#5865f2] text-white shadow-lg shadow-[#5865f2]/40">
                <Dices className="h-7 w-7" />
              </div>
              <div>
                <h1 className="font-display text-2xl sm:text-4xl font-extrabold uppercase tracking-tight text-white">
                  Decision Blackjack Benchmark
                </h1>
                <p className="text-sm text-[#949ba4] font-medium">
                  Deterministic casino simulation testbed comparing AI decision
                  engines against game theory.
                </p>
              </div>
            </div>

            {/* Feature Pills */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              <div className="flex items-center space-x-2 rounded-sm border border-[#2b305c]/80 bg-[#0a0d3a]/70 px-3 py-2 text-xs text-white">
                <Cpu className="h-4 w-4 text-[#ec48bd] shrink-0" />
                <span className="truncate">Jev & Laya AI Inference</span>
              </div>
              <div className="flex items-center space-x-2 rounded-sm border border-[#2b305c]/80 bg-[#0a0d3a]/70 px-3 py-2 text-xs text-white">
                <ShieldCheck className="h-4 w-4 text-[#35ed7e] shrink-0" />
                <span className="truncate">Basic Strategy Oracle</span>
              </div>
              <div className="flex items-center space-x-2 rounded-sm border border-[#2b305c]/80 bg-[#0a0d3a]/70 px-3 py-2 text-xs text-white">
                <Zap className="h-4 w-4 text-[#fee75c] shrink-0" />
                <span className="truncate">Deterministic Multi-Deck Shoes</span>
              </div>
            </div>
          </div>
        </div>

        {/* Configuration Form */}
        <SimulationConfigForm
          onSubmit={handleSubmit}
          isLoading={isSubmitting}
        />
      </div>
    </div>
  );
};
