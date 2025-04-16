
const ModuleCard: React.FC<any> = ({ data }) => {
    return (
        <div className="w-full h-[320px] !rounded-lg bg-[#FDFDFD] " >
            <div className="flex justify-start items-center bg-[#E6FEE7] p-3 rounded-t-[5px]">
                <img src={data?.icon} className="mx-2" />
                <div className="text-[#535862] font-[600] !text-[16px]"> {data?.name}</div>
            </div>
            <div className="w-full !h-[calc(320px-10%)] overflow-y-auto !rounded-lg grid grid-cols-2 md:grid-cols-3 gap-4 !p-6 mb-4">
                {data?.apps?.map((subdata: any) => (
                    <div
                        key={subdata?.idx}
                        onClick={() => window.location.href = subdata?.route}
                        className="flex flex-col items-center cursor-pointer group"
                    >
                        <div className="py-3 px-2 rounded-[5px] bg-[#F5F5F5] border-[1px] border-[#F5F5F5] group-hover:bg-[#E6FEE7] transition-all duration-300">
                            <div className="flex items-center justify-center transition-transform duration-300 group-hover:scale-125">
                                <img src={subdata?.icon} className="px-1"/>
                            </div>
                        </div>
                        <h1
                            className="font-[500] my-2 text-sm leading-none text-center text-[#535862] transition-all duration-300 group-hover:text-[#222]"
                        >
                            {subdata?.label?.split(' ').length > 1 ? (
                                <>
                                    {subdata?.label?.split(' ')[0]} <br /> {subdata?.label?.split(' ').slice(1).join(' ')}
                                </>
                            ) : (
                                subdata?.label
                            )}
                        </h1>
                    </div>
                ))}
            </div>

        </div>
    )
}

export default ModuleCard