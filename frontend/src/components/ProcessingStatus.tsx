type Props = {
    progress: number;
};

export default function ProcessingStatus({
    progress,
}: Props) {
    return (
        <div className="processing-status">
            <h2>Processing...</h2>

            <progress
                value={progress}
                max={100}
            />

            <p>{progress}%</p>
        </div>
    );
}