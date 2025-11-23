import { ICON_OPTIONS } from "../../constants/icons";

type Props = {
  selected: string;
  onSelect: (iconName: string) => void;
  options: typeof ICON_OPTIONS;
};

export const PersonaIconSelector: React.FC<Props> = ({ selected, onSelect, options }) => {
  return (
    <div className="grid grid-cols-4 gap-4">
      {options.map(({ name, Component }) => (
        <div
          key={name}
          onClick={() => onSelect(name)}
          className={`cursor-pointer rounded-lg p-2 border transition ${
            selected === name
              ? "border-fuchsia-500 bg-purple-800"
              : "border-purple-800 bg-black/40"
          }`}
        >
          <Component className="w-6 h-6 mx-auto text-purple-200" />
        </div>
      ))}
    </div>
  );
};
