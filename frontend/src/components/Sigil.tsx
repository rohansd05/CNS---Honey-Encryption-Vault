import type { Sigil as SigilType } from '@/api/types';

interface SigilProps {
  sigil: SigilType;
  size?: 'sm' | 'md' | 'lg';
}

export function Sigil({ sigil, size = 'md' }: SigilProps) {
  const sizes = {
    sm: { container: 'w-12 h-12', text: 'text-sm', ring: 'ring-2' },
    md: { container: 'w-24 h-24', text: 'text-2xl', ring: 'ring-4' },
    lg: { container: 'w-32 h-32', text: 'text-4xl', ring: 'ring-[6px]' },
  };
  
  return (
    <div className="flex flex-col items-center gap-4">
      <div 
        className={`flex items-center justify-center rounded-full bg-slate-900 ${sizes[size].container} ${sizes[size].ring}`}
        style={{ borderColor: sigil.color, boxShadow: `0 0 20px ${sigil.color}40` }}
        title="Your Vault Sigil"
      >
        <span className={sizes[size].text}>
          {sigil.emojis.join('')}
        </span>
      </div>
    </div>
  );
}
