import React, { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import {
  VariantRulesFormValues,
  DEFAULT_VARIANT_RULES,
} from '../types/simulation';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Button } from '../components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Play, Zap, AlertCircle } from 'lucide-react';

interface SimulationConfigFormProps {
  onSubmit: (values: VariantRulesFormValues) => Promise<void>;
  isLoading?: boolean;
}

export const SimulationConfigForm: React.FC<SimulationConfigFormProps> = ({
  onSubmit,
  isLoading = false,
}) => {
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors },
  } = useForm<VariantRulesFormValues>({
    defaultValues: DEFAULT_VARIANT_RULES,
  });

  const selectedPlayers = watch('selected_players');

  const atLeastOnePlayer =
    selectedPlayers.jev || selectedPlayers.laya || selectedPlayers.optimal;

  const handleLaunch = (mode: 'visualized' | 'fast_batch') => {
    return handleSubmit(async (data) => {
      setFormError(null);

      if (!atLeastOnePlayer) {
        setFormError('At least one player (Jev, Laya, or Basic Strategy) must be selected.');
        return;
      }

      if (data.min_bet > data.max_bet) {
        setFormError(`Minimum bet ($${data.min_bet}) cannot exceed maximum bet ($${data.max_bet}).`);
        return;
      }

      if (data.initial_bankroll < data.min_bet) {
        setFormError(
          `Initial bankroll ($${data.initial_bankroll}) must be at least table minimum bet ($${data.min_bet}).`
        );
        return;
      }

      try {
        await onSubmit({
          ...data,
          execution_mode: mode,
          min_bet: Number(data.min_bet),
          max_bet: Number(data.max_bet),
          initial_bankroll: Number(data.initial_bankroll),
          max_rounds: Number(data.max_rounds),
          burn_cards_count: Number(data.burn_cards_count),
          penetration: Number(data.penetration),
          max_split_hands: Number(data.max_split_hands),
          num_decks: Number(data.num_decks) as any,
          blackjack_payout: Number(data.blackjack_payout) as any,
          delay_ms: Number(data.delay_ms || 300),
          seed: data.seed ? Number(data.seed) : null,
        });
      } catch (err: any) {
        setFormError(err.message || 'Failed to initialize simulation session.');
      }
    });
  };

  return (
    <form className="space-y-6">
      {formError && (
        <div className="flex items-center space-x-2 rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{formError}</span>
        </div>
      )}

      {/* 1. Player Participation Selection */}
      <Card className="border-slate-800 bg-slate-900/60 shadow-md">
        <CardHeader className="pb-3">
          <CardTitle className="text-base text-slate-100">Benchmarked Players</CardTitle>
          <CardDescription className="text-slate-400">
            Select the entities participating in the benchmark. Deselected players will display an empty table and darkened stats.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {/* Jev */}
            <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/40 p-3">
              <div className="space-y-0.5">
                <div className="flex items-center space-x-2">
                  <span className="h-3 w-3 rounded-full bg-[rgb(213,120,190)]" />
                  <Label htmlFor="player-jev" className="cursor-pointer font-medium text-slate-200">
                    Jev (System One)
                  </Label>
                </div>
                <p className="text-xs text-slate-400">Agentic probability judge</p>
              </div>
              <Controller
                name="selected_players.jev"
                control={control}
                render={({ field }) => (
                  <Switch
                    id="player-jev"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                )}
              />
            </div>

            {/* Laya */}
            <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/40 p-3">
              <div className="space-y-0.5">
                <div className="flex items-center space-x-2">
                  <span className="h-3 w-3 rounded-full bg-[rgb(68,120,208)]" />
                  <Label htmlFor="player-laya" className="cursor-pointer font-medium text-slate-200">
                    Laya (Local)
                  </Label>
                </div>
                <p className="text-xs text-slate-400">Local inference benchmark</p>
              </div>
              <Controller
                name="selected_players.laya"
                control={control}
                render={({ field }) => (
                  <Switch
                    id="player-laya"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                )}
              />
            </div>

            {/* Basic Strategy */}
            <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/40 p-3">
              <div className="space-y-0.5">
                <div className="flex items-center space-x-2">
                  <span className="h-3 w-3 rounded-full bg-[rgb(118,194,154)]" />
                  <Label htmlFor="player-optimal" className="cursor-pointer font-medium text-slate-200">
                    Basic Strategy
                  </Label>
                </div>
                <p className="text-xs text-slate-400">Mathematically optimal baseline</p>
              </div>
              <Controller
                name="selected_players.optimal"
                control={control}
                render={({ field }) => (
                  <Switch
                    id="player-optimal"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                )}
              />
            </div>
          </div>
          {!atLeastOnePlayer && (
            <p className="mt-2 text-xs text-rose-400">
              * At least one player must be selected to run a simulation.
            </p>
          )}
        </CardContent>
      </Card>

      {/* 2. Table & Casino Rules */}
      <Card className="border-slate-800 bg-slate-900/60 shadow-md">
        <CardHeader className="pb-3">
          <CardTitle className="text-base text-slate-100">House & Dealer Rules</CardTitle>
          <CardDescription className="text-slate-400">
            Configure Blackjack game mechanics based on casino variant specifications.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {/* Soft 17 */}
          <div className="space-y-1.5">
            <Label htmlFor="soft_17_rule" className="text-xs text-slate-300">
              Dealer Soft 17
            </Label>
            <Select id="soft_17_rule" {...register('soft_17_rule')}>
              <option value="S17" className="bg-slate-900 text-slate-100">
                S17 - Dealer Stands on Soft 17
              </option>
              <option value="H17" className="bg-slate-900 text-slate-100">
                H17 - Dealer Hits Soft 17
              </option>
            </Select>
          </div>

          {/* Blackjack Payout */}
          <div className="space-y-1.5">
            <Label htmlFor="blackjack_payout" className="text-xs text-slate-300">
              Natural Blackjack Payout
            </Label>
            <Select id="blackjack_payout" {...register('blackjack_payout')}>
              <option value={1.5} className="bg-slate-900 text-slate-100">
                3:2 (Standard, 1.5x)
              </option>
              <option value={1.2} className="bg-slate-900 text-slate-100">
                6:5 (Unfavorable, 1.2x)
              </option>
              <option value={1.0} className="bg-slate-900 text-slate-100">
                1:1 (Even Money, 1.0x)
              </option>
            </Select>
          </div>

          {/* Hole Card Rule */}
          <div className="space-y-1.5">
            <Label htmlFor="hole_card_rule" className="text-xs text-slate-300">
              Hole Card Style
            </Label>
            <Select id="hole_card_rule" {...register('hole_card_rule')}>
              <option value="AMERICAN_PEEK" className="bg-slate-900 text-slate-100">
                American Style (Dealer Peeks)
              </option>
              <option value="EUROPEAN_NO_HOLE_CARD" className="bg-slate-900 text-slate-100">
                European Style (ENHC - No Hole Card)
              </option>
            </Select>
          </div>

          {/* Surrender Rule */}
          <div className="space-y-1.5">
            <Label htmlFor="surrender_rule" className="text-xs text-slate-300">
              Surrender Rule
            </Label>
            <Select id="surrender_rule" {...register('surrender_rule')}>
              <option value="LATE" className="bg-slate-900 text-slate-100">
                Late Surrender (After Peek)
              </option>
              <option value="EARLY" className="bg-slate-900 text-slate-100">
                Early Surrender (Before Peek)
              </option>
              <option value="NO_SURRENDER" className="bg-slate-900 text-slate-100">
                No Surrender Permitted
              </option>
            </Select>
          </div>

          {/* Insurance Switch */}
          <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/40 p-3">
            <div className="space-y-0.5">
              <Label htmlFor="insurance_allowed" className="text-xs text-slate-200">
                Insurance Side Bet (2:1)
              </Label>
              <p className="text-[11px] text-slate-400">Offer insurance on Dealer Ace</p>
            </div>
            <Controller
              name="insurance_allowed"
              control={control}
              render={({ field }) => (
                <Switch
                  id="insurance_allowed"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
          </div>

          {/* Double After Split */}
          <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/40 p-3">
            <div className="space-y-0.5">
              <Label htmlFor="double_after_split" className="text-xs text-slate-200">
                Double After Split (DAS)
              </Label>
              <p className="text-[11px] text-slate-400">Allow doubling post-split</p>
            </div>
            <Controller
              name="double_after_split"
              control={control}
              render={({ field }) => (
                <Switch
                  id="double_after_split"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
          </div>
        </CardContent>
      </Card>

      {/* 3. Splits & Shoe Setup */}
      <Card className="border-slate-800 bg-slate-900/60 shadow-md">
        <CardHeader className="pb-3">
          <CardTitle className="text-base text-slate-100">Splits & Shoe Configuration</CardTitle>
          <CardDescription className="text-slate-400">
            Decks, penetration threshold, burn cards, and resplit conditions.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {/* Decks */}
          <div className="space-y-1.5">
            <Label htmlFor="num_decks" className="text-xs text-slate-300">
              Shoe Decks
            </Label>
            <Select id="num_decks" {...register('num_decks')}>
              <option value={1} className="bg-slate-900 text-slate-100">
                1 Deck (Single Deck)
              </option>
              <option value={2} className="bg-slate-900 text-slate-100">
                2 Decks (Double Deck)
              </option>
              <option value={4} className="bg-slate-900 text-slate-100">
                4 Decks
              </option>
              <option value={6} className="bg-slate-900 text-slate-100">
                6 Decks (Shoe Standard)
              </option>
              <option value={8} className="bg-slate-900 text-slate-100">
                8 Decks (Casino Shoe)
              </option>
            </Select>
          </div>

          {/* Penetration */}
          <div className="space-y-1.5">
            <Label htmlFor="penetration" className="text-xs text-slate-300">
              Penetration Threshold (50% - 85%)
            </Label>
            <Input
              id="penetration"
              type="number"
              step="0.05"
              min="0.50"
              max="0.85"
              {...register('penetration', {
                valueAsNumber: true,
                min: { value: 0.5, message: 'Min penetration is 0.50' },
                max: { value: 0.85, message: 'Max penetration is 0.85' },
              })}
            />
            {errors.penetration && (
              <p className="text-xs text-rose-400">{errors.penetration.message}</p>
            )}
          </div>

          {/* Max Split Hands */}
          <div className="space-y-1.5">
            <Label htmlFor="max_split_hands" className="text-xs text-slate-300">
              Max Split Hands (1–4)
            </Label>
            <Input
              id="max_split_hands"
              type="number"
              min="1"
              max="4"
              {...register('max_split_hands', {
                valueAsNumber: true,
                min: 1,
                max: 4,
              })}
            />
          </div>

          {/* Burn Cards */}
          <div className="space-y-1.5">
            <Label htmlFor="burn_cards_count" className="text-xs text-slate-300">
              Burn Cards (0–5)
            </Label>
            <Input
              id="burn_cards_count"
              type="number"
              min="0"
              max="5"
              {...register('burn_cards_count', { valueAsNumber: true })}
            />
          </div>

          {/* Re-split Aces */}
          <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/40 p-3 sm:col-span-2">
            <div className="space-y-0.5">
              <Label htmlFor="resplit_aces" className="text-xs text-slate-200">
                Re-Split Aces (RSA)
              </Label>
              <p className="text-[11px] text-slate-400">Allow re-splitting pairs of Aces</p>
            </div>
            <Controller
              name="resplit_aces"
              control={control}
              render={({ field }) => (
                <Switch
                  id="resplit_aces"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
          </div>

          {/* Hit Split Aces */}
          <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/40 p-3 sm:col-span-2">
            <div className="space-y-0.5">
              <Label htmlFor="hit_split_aces" className="text-xs text-slate-200">
                Hit Split Aces
              </Label>
              <p className="text-[11px] text-slate-400">Allow hitting Aces after splitting</p>
            </div>
            <Controller
              name="hit_split_aces"
              control={control}
              render={({ field }) => (
                <Switch
                  id="hit_split_aces"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
          </div>
        </CardContent>
      </Card>

      {/* 4. Economics & Limits */}
      <Card className="border-slate-800 bg-slate-900/60 shadow-md">
        <CardHeader className="pb-3">
          <CardTitle className="text-base text-slate-100">Bankroll & Table Wager Limits</CardTitle>
          <CardDescription className="text-slate-400">
            Define starting funds and min/max table limits.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {/* Starting Bankroll */}
          <div className="space-y-1.5">
            <Label htmlFor="initial_bankroll" className="text-xs text-slate-300">
              Starting Bankroll ($)
            </Label>
            <Input
              id="initial_bankroll"
              type="number"
              step="10"
              min="10"
              {...register('initial_bankroll', { valueAsNumber: true })}
            />
          </div>

          {/* Min Bet */}
          <div className="space-y-1.5">
            <Label htmlFor="min_bet" className="text-xs text-slate-300">
              Minimum Bet ($)
            </Label>
            <Input
              id="min_bet"
              type="number"
              step="1"
              min="1"
              {...register('min_bet', { valueAsNumber: true })}
            />
          </div>

          {/* Max Bet */}
          <div className="space-y-1.5">
            <Label htmlFor="max_bet" className="text-xs text-slate-300">
              Maximum Bet ($)
            </Label>
            <Input
              id="max_bet"
              type="number"
              step="10"
              min="10"
              {...register('max_bet', { valueAsNumber: true })}
            />
          </div>
        </CardContent>
      </Card>

      {/* 5. Scope & Simulation Mode */}
      <Card className="border-slate-800 bg-slate-900/60 shadow-md">
        <CardHeader className="pb-3">
          <CardTitle className="text-base text-slate-100">Simulation Controls & Modes</CardTitle>
          <CardDescription className="text-slate-400">
            Pacing, rounds count, reproducibility seed, and offline mock execution.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {/* Max Rounds */}
          <div className="space-y-1.5">
            <Label htmlFor="max_rounds" className="text-xs text-slate-300">
              Max Benchmark Rounds (1–100,000)
            </Label>
            <Input
              id="max_rounds"
              type="number"
              min="1"
              max="100000"
              {...register('max_rounds', { valueAsNumber: true })}
            />
          </div>

          {/* Seed */}
          <div className="space-y-1.5">
            <Label htmlFor="seed" className="text-xs text-slate-300">
              PRNG Seed (Optional, integer)
            </Label>
            <Input
              id="seed"
              type="number"
              placeholder="e.g. 42"
              {...register('seed')}
            />
          </div>

          {/* Visualizer Pacing Delay */}
          <div className="space-y-1.5">
            <Label htmlFor="delay_ms" className="text-xs text-slate-300">
              Visualizer Delay (0–2,000 ms)
            </Label>
            <Input
              id="delay_ms"
              type="number"
              min="0"
              max="2000"
              step="50"
              {...register('delay_ms', { valueAsNumber: true })}
            />
          </div>

          {/* Mock Mode Switch */}
          <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/40 p-3 sm:col-span-3">
            <div className="space-y-0.5">
              <Label htmlFor="mock_mode" className="text-xs text-slate-200">
                Offline Mock Mode
              </Label>
              <p className="text-[11px] text-slate-400">
                Run with high-speed synthetic AI models without requiring live external network APIs
              </p>
            </div>
            <Controller
              name="mock_mode"
              control={control}
              render={({ field }) => (
                <Switch
                  id="mock_mode"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              )}
            />
          </div>
        </CardContent>
      </Card>

      {/* Dual Launch Action Buttons */}
      <div className="flex flex-col items-center justify-end gap-3 sm:flex-row pt-4">
        {/* Path 1: Fast Batch */}
        <Button
          type="button"
          variant="secondary"
          disabled={isLoading || !atLeastOnePlayer}
          onClick={handleLaunch('fast_batch')}
          className="w-full sm:w-auto h-11 px-6 border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-100 font-medium"
        >
          <Zap className="mr-2 h-4 w-4 text-amber-400" />
          Launch Fast Batch (Path 1)
        </Button>

        {/* Path 2: Real-Time Visualizer */}
        <Button
          type="button"
          disabled={isLoading || !atLeastOnePlayer}
          onClick={handleLaunch('visualized')}
          className="w-full sm:w-auto h-11 px-6 bg-emerald-600 hover:bg-emerald-500 text-white font-medium shadow-lg shadow-emerald-950/50"
        >
          <Play className="mr-2 h-4 w-4" />
          Launch Visualizer (Path 2)
        </Button>
      </div>
    </form>
  );
};
