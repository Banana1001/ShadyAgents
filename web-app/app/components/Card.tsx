type CardProps = {
    type: 'action' | 'idea' | 'generated';
    content: string;
};

export default function Card({ content }: CardProps) {
    return (
        <div className="bg-white dark:bg-gray-800 shadow-md rounded-lg p-4 w-[250px] shrink-0">
            <p className="text-gray-800 dark:text-white text-sm">{content}</p>
        </div>
    );
}
