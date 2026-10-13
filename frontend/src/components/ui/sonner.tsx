import { Toaster as Sonner } from 'sonner';
import { useTheme } from '@/lib/theme';

type ToasterProps = React.ComponentProps<typeof Sonner>;

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme } = useTheme();

  return (
    <Sonner
      theme={theme}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            'group toast group-[.toaster]:bg-bg-surface group-[.toaster]:text-text-primary group-[.toaster]:border-border group-[.toaster]:shadow-lg',
          description: 'group-[.toast]:text-text-secondary',
          actionButton:
            'group-[.toast]:bg-accent group-[.toast]:text-black font-semibold',
          cancelButton:
            'group-[.toast]:bg-bg-elevated group-[.toast]:text-text-secondary',
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
