type Props = {
    onSelect: (file: File) => void;
    onDetect: () => void;
    disabled: boolean;
};

export default function UploadBox({
    onSelect,
    onDetect,
    disabled,
}: Props) {
    return (
        <div className="upload-box">
            <h3>Upload Match Video</h3>
            <label className = 'upload-area'>
                <input
                    type="file"
                    accept="video/*"
                    onChange={(e) => {
                        const file = e.target.files?.[0];

                        if (file) {
                            onSelect(file);
                        }
                    }}
                />

                <span>Click to choose video</span>
            </label>

            <button 
                onClick = {onDetect}
                disabled = {disabled}
            >
                Detect Highlights
            </button>
        </div>
    );
}