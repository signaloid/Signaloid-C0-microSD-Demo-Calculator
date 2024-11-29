#include <uxhw.h>
#include "C0microSDConstants.h"

typedef enum
{
	kCalculateNoCommand		= 0, /* Go to idle */
	kCalculateAddition		= 1, /* Calculate addition */
	kCalculateSubtraction		= 2, /* Calculate Subtraction */
	kCalculateMultiplication	= 3, /* Calculate Multiplication */
	kCalculateDivision		= 4, /* Calculate Division */
	kCalculateSample		= 5, /* Calculate Sample */
} SignaloidSoCCommand;

int
main(void)
{
	volatile SignaloidSoCStatus *	mmioStatus		= (SignaloidSoCStatus *) kSignaloidSoCDeviceConstantsStatusAddress;
	volatile uint32_t *		mmioSoCControl		= (uint32_t *) kSignaloidSoCDeviceConstantsSoCControlAddress;
	volatile SignaloidSoCCommand *	mmioCommand		= (SignaloidSoCCommand *) kSignaloidSoCDeviceConstantsCommandAddress;

	volatile double *		MOSIBuffer		= (double *) kSignaloidSoCDeviceConstantsMOSIBufferAddress;
	volatile uint32_t *		MOSIBufferUInt		= (uint32_t *) kSignaloidSoCDeviceConstantsMOSIBufferAddress;

	volatile double *		MISOBuffer		= (double *) kSignaloidSoCDeviceConstantsMISOBufferAddress;
	volatile uint32_t *		resultBufferSize	= (uint32_t *) kSignaloidSoCDeviceConstantsMISOBufferAddress;
	volatile uint8_t *		resultBuffer		= (uint8_t *) (kSignaloidSoCDeviceConstantsMISOBufferAddress + sizeof(uint32_t));

	volatile double 		argument0 		= UxHwDoubleUniformDist(1.0, 2.0);
	double				argument1;	
	double				argument2;

	uint32_t			resultSize;
	double				result;

	/*
	 *	Generate a distribution from weighted samples from a Gaussian distribution
	 *	with mean value zero and standard deviation equal to one.
	 */
	WeightedDoubleSample	weightedSamples[16] =
					{
						{.sample = -2.2194097942437231, .sampleWeight = 0.0339789420851602},
						{.sample = -1.5678879053053274, .sampleWeight = 0.0520280112620429},
						{.sample = -1.1997100902860450, .sampleWeight = 0.0601091352703015},
						{.sample = -0.9205473016275229, .sampleWeight = 0.0663526532241763},
						{.sample = -0.6859608829556935, .sampleWeight = 0.0686569819948156},
						{.sample = -0.4772650338604341, .sampleWeight = 0.0714941307381180},
						{.sample = -0.2817093825097764, .sampleWeight = 0.0732557829230397},
						{.sample = -0.0931705533484249, .sampleWeight = 0.0741243625023456},
						{.sample =  0.0931705533484249, .sampleWeight = 0.0741243625023456},
						{.sample =  0.2817093825097764, .sampleWeight = 0.0732557829230397},
						{.sample =  0.4772650338604341, .sampleWeight = 0.0714941307381180},
						{.sample =  0.6859608829556935, .sampleWeight = 0.0686569819948156},
						{.sample =  0.9205473016275229, .sampleWeight = 0.0663526532241763},
						{.sample =  1.1997100902860450, .sampleWeight = 0.0601091352703015},
						{.sample =  1.5678879053053274, .sampleWeight = 0.0520280112620429},
						{.sample =  2.2194097942437231, .sampleWeight = 0.0339789420851602},
					};

	double generatedDistribution;

	while (1)
	{
		/*
		 *	Set status to "waitingForCommand"
		 */
		*mmioStatus = kSignaloidSoCStatusWaitingForCommand;

		/*
		 *	Block until command is issued
		 */
		while (*mmioCommand == kCalculateNoCommand) {}

		/*
		 *	Set status to inform host that calculation will start
		 */
		*mmioStatus = kSignaloidSoCStatusCalculating;

		/*
		 *	Turn on status LED
		 */
		*mmioSoCControl = 0xffffffff;
		switch (*mmioCommand)
		{	
			/*
			 *	All of the following commands parse the inputs in the same way
			 */
			case kCalculateAddition:
			case kCalculateSubtraction:
			case kCalculateMultiplication:
			case kCalculateDivision:

				/*
				 *	Parse inputs
				 */
				argument1 = UxHwDoubleUniformDist(MOSIBuffer[0], MOSIBuffer[1]);
				argument2 = UxHwDoubleUniformDist(MOSIBuffer[2], MOSIBuffer[3]);

				/*
				 *	Calculate
				 */
				switch (*mmioCommand)
				{
					case kCalculateAddition:
						result = argument1 + argument2;
						break;
					case kCalculateSubtraction:
						result = argument1 - argument2;
						break;
					case kCalculateMultiplication:
						result = argument1 * argument2;
						break;
					case kCalculateDivision:
						result = argument1 / argument2;
						break;
					default:
						break;
				}

				/*
				 *	Pack result
				 */
				resultSize = UxHwDoubleDistributionToByteArray(result, resultBuffer, kSignaloidSoCCommonConstantsMISOBufferSizeBytes - sizeof(uint32_t));
				*resultBufferSize = resultSize;

				/*
				 *	Set status
				 */
				*mmioStatus = kSignaloidSoCStatusDone;
				break;
			case kCalculateSample:
				generatedDistribution = UxHwDoubleDistFromWeightedSamples(weightedSamples, 16, 16);
				UxHwDoubleSampleBatch(generatedDistribution, MISOBuffer, MOSIBufferUInt[0]);

				/*
				 *	Set status
				 */
				*mmioStatus = kSignaloidSoCStatusDone;
				break;
			default:
				*mmioStatus = kSignaloidSoCStatusInvalidCommand;
				break;
		}

		/*
		 *	Turn off status LED
		 */
		*mmioSoCControl = 0x00000000;

		/*
		 *	Block until command is cleared
		 */
		while (*mmioCommand != kCalculateNoCommand) {}
	}
}
