import React from "react";
import { ToastContainer, type ToastContainerProps } from "react-toastify";
import { useTheme } from "../theme/ThemeContext";

type Props = Omit<ToastContainerProps, "theme">;

/** Toast theme follows app light/dark preference. */
export const ThemedToastContainer: React.FC<Props> = (props) => {
  const { theme } = useTheme();
  return (
    <ToastContainer
      {...props}
      theme={theme === "light" ? "light" : "dark"}
    />
  );
};
