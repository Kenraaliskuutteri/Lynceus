import React from 'react';

interface RangeOption {
  label: string;
  minutes: number;
}

const RANGES: RangeOption[] = [
  { label: '15m', minutes: 15 },
  { label: '1h', minutes: 60 },
  { label: '6h', minutes: 360 },
  { label: '24h', minutes: 1440 },
];

interface Props {
  value: number;
  onChange: (minutes: number) => void;
}

export const RangeSelector: React.FC<Props> = ({ value, onChange }) => {
  return (
    <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
      {RANGES.map((range) => (
        <button
          key={range.minutes}
          className="secondary-button"
          style={{
            opacity: value === range.minutes ? 1 : 0.6,
            fontWeight: value === range.minutes ? 700 : 400,
          }}
          onClick={() => onChange(range.minutes)}
        >
          {range.label}
        </button>
      ))}
    </div>
  );
};

export default RangeSelector;