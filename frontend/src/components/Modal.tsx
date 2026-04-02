import React, { ReactNode } from "react";

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-black/80 border border-purple-800 rounded-2xl p-6 max-w-lg w-full">
        {children}

        {showCloseButton && (
          <button
            type="button"
            onClick={onClose}
            className="mt-4 w-full rounded-xl bg-purple-700 hover:bg-purple-600 text-white py-2 font-medium transition-colors"
          >
            Close
          </button>
        )}
      </div>
    </div>
  );
};
