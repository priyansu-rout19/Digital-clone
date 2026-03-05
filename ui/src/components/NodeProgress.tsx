interface NodeProgressProps {
  currentNode: string | null;
}

export default function NodeProgress({ currentNode }: NodeProgressProps) {
  if (!currentNode) return null;

  return (
    <div className="flex items-center gap-3 px-4 py-3 mx-auto max-w-2xl">
      <div className="flex gap-1">
        <span className="w-2 h-2 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-2 h-2 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-2 h-2 bg-para-teal rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
      <span className="text-sm text-gray-400">{currentNode}</span>
    </div>
  );
}
