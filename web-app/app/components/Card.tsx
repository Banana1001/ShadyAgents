export type CardProps = {
    type: 'action' | 'idea' | 'generated';
    content: string;
};

export default function Card({ type, content }: CardProps) {
    return (
        <div
            draggable
            onDragStart={(e) => {
                e.dataTransfer.setData('text/plain', JSON.stringify({ type, content }));
            }}
            className="bg-white dark:bg-gray-800 shadow-md rounded-lg p-4 w-[250px] shrink-0 cursor-grab"
        >
            <p className="text-gray-800 dark:text-white text-sm">{content}</p>
        </div>
    );
}
