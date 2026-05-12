import { useState } from "react";

interface Props {
  onSubmit: (title: string, department: string, description: string) => void;
  onClose: () => void;
}

export default function ScoreRoleForm({ onSubmit, onClose }: Props) {
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;
    onSubmit(title.trim(), department.trim(), description.trim());
  };

  return (
    <div className="fixed inset-0 bg-ink-950/85 backdrop-blur-md flex items-center justify-center z-50">
      <div className="bg-ink-900 hair-t hair-b hair-l hair-r w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto animate-scale-in relative">
        {/* Corner crops */}
        <div className="absolute top-2 left-2 w-2 h-2 border-l border-t border-volt-400 pointer-events-none" />
        <div className="absolute top-2 right-2 w-2 h-2 border-r border-t border-volt-400 pointer-events-none" />

        <div className="px-8 pt-7 pb-5 hair-b">
          <div className="flex items-baseline justify-between">
            <div>
              <p className="font-mono text-[10px] tracking-[0.3em] text-volt-400 uppercase mb-2">
                § New Entry
              </p>
              <h2 className="font-serif text-3xl font-light italic tracking-tight">
                Score a role
              </h2>
            </div>
            <button
              onClick={onClose}
              className="text-bone-400 hover:text-bone-100 text-2xl cursor-pointer transition-colors w-9 h-9 flex items-center justify-center font-light"
              aria-label="Close"
            >
              ×
            </button>
          </div>
          <p className="text-bone-400 text-sm mt-3 max-w-md leading-relaxed">
            Provide a role title and its description. ARIA will score it across eleven variables
            and recommend a strategy.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="px-8 py-7 space-y-6">
          <Field
            label="Role Title"
            index="01"
            required
            value={title}
            onChange={setTitle}
            placeholder="e.g. Financial Analyst"
          />
          <Field
            label="Department"
            index="02"
            value={department}
            onChange={setDepartment}
            placeholder="e.g. Finance"
          />
          <div>
            <FieldLabel label="Job Description" index="03" required />
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Paste the full job description here…"
              rows={10}
              className="w-full bg-ink-950 border border-bone-100/10 px-4 py-3 text-sm text-bone-100 placeholder:text-bone-500 focus:border-volt-400 focus:bg-ink-950 outline-none resize-y transition-colors font-sans"
              required
            />
          </div>

          <div className="flex items-center justify-between gap-3 pt-3 hair-t -mx-8 px-8 pt-6">
            <span className="font-mono text-[10px] tracking-[0.2em] text-bone-400 uppercase">
              ↩ Enter to submit
            </span>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2.5 text-sm text-bone-300 hover:text-bone-100 cursor-pointer transition-colors font-mono tracking-[0.1em] uppercase text-[11px]"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="group px-6 py-2.5 bg-volt-400 text-ink-950 font-medium text-[13px] tracking-tight cursor-pointer hover:bg-volt-300 transition-all active:scale-[0.98]"
                style={{ clipPath: "polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px)" }}
              >
                <span className="font-mono text-[10px] tracking-[0.2em] opacity-70 mr-2">→</span>
                <span className="font-serif italic">Analyse role</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({
  label,
  index,
  required,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  index: string;
  required?: boolean;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div>
      <FieldLabel label={label} index={index} required={required} />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        className="w-full bg-ink-950 border border-bone-100/10 px-4 py-3 text-sm text-bone-100 placeholder:text-bone-500 focus:border-volt-400 outline-none transition-colors font-sans"
      />
    </div>
  );
}

function FieldLabel({ label, index, required }: { label: string; index: string; required?: boolean }) {
  return (
    <div className="flex items-baseline gap-2 mb-2.5">
      <span className="font-mono text-[10px] tracking-[0.25em] text-bone-400 uppercase">
        {index} ·
      </span>
      <span className="font-mono text-[10px] tracking-[0.25em] text-bone-200 uppercase">
        {label}
      </span>
      {required && <span className="text-volt-400 text-xs leading-none">*</span>}
    </div>
  );
}
