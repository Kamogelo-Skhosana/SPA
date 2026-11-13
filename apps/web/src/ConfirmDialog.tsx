import { useEffect, useRef, type ReactNode } from 'react';
export default function ConfirmDialog({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    panel.current?.querySelector<HTMLElement>('button')?.focus();
    return () => previous?.focus();
  }, []);
  return <div className="dialog-backdrop"><section ref={panel} className="confirm-dialog panel" role="dialog" aria-modal="true" aria-label={title}
    onKeyDown={event => {
      if (event.key === 'Escape') { event.stopPropagation(); onClose(); }
      if (event.key === 'Tab') {
        const controls = panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), a[href]');
        if (!controls?.length) { event.preventDefault(); return; }
        const first = controls[0], last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    }}><h2>{title}</h2>{children}</section></div>;
}
