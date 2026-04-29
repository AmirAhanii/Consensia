import React, { ReactNode } from "react";
import { X } from "lucide-react";

type ModalProps = {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  showCloseButton?: boolean;
};

export const Modal: React.FC<ModalProps> = ({
  open,
  onClose,
  children,
  showCloseButton = true,
}) => {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="relative bg-black/80 border border-purple-800 rounded-2xl p-6 max-w-lg w-full max-h-[85vh] flex flex-col">
        {showCloseButton && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="absolute top-3 right-3 z-10 rounded-lg p-1.5 text-purple-400 hover:text-white hover:bg-purple-800/50 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
        <div className="overflow-y-auto flex-1 pr-1">
          {children}
        </div>
      </div>
    </div>
  );
};
