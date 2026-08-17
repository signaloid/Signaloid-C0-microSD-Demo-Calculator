/*
 *	Copyright (c) 2026, Signaloid.
 *
 *	Permission is hereby granted, free of charge, to any person obtaining a copy
 *	of this software and associated documentation files (the "Software"), to deal
 *	in the Software without restriction, including without limitation the rights
 *	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 *	copies of the Software, and to permit persons to whom the Software is
 *	furnished to do so, subject to the following conditions:
 *
 *	The above copyright notice and this permission notice shall be included in all
 *	copies or substantial portions of the Software.
 *
 *	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 *	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 *	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 *	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 *	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 *	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 *	SOFTWARE.
 */


#include <uxhw.h>
#include "C0HAL.h"


typedef enum
{
	kCalculateNoCommand         = 0,
	kCalculateAddition          = 1,
	kCalculateSubtraction       = 2,
	kCalculateMultiplication    = 3,
	kCalculateDivision          = 4,
	kCalculateSample            = 5,
} SignaloidSoCCommand;

enum
{
	kWeightedSampleCount = 16
};

/*
 *	Generate a distribution from weighted samples from a Gaussian distribution
 *	with mean value zero and standard deviation equal to one.
 */
WeightedFloatSample weightedSamples[kWeightedSampleCount] = {
	{ .sample = -2.2194097942437231, .sampleWeight = 0.0339789420851602 },
	{ .sample = -1.5678879053053274, .sampleWeight = 0.0520280112620429 },
	{ .sample = -1.1997100902860450, .sampleWeight = 0.0601091352703015 },
	{ .sample = -0.9205473016275229, .sampleWeight = 0.0663526532241763 },
	{ .sample = -0.6859608829556935, .sampleWeight = 0.0686569819948156 },
	{ .sample = -0.4772650338604341, .sampleWeight = 0.0714941307381180 },
	{ .sample = -0.2817093825097764, .sampleWeight = 0.0732557829230397 },
	{ .sample = -0.0931705533484249, .sampleWeight = 0.0741243625023456 },
	{ .sample = 0.0931705533484249,  .sampleWeight = 0.0741243625023456 },
	{ .sample = 0.2817093825097764,  .sampleWeight = 0.0732557829230397 },
	{ .sample = 0.4772650338604341,  .sampleWeight = 0.0714941307381180 },
	{ .sample = 0.6859608829556935,  .sampleWeight = 0.0686569819948156 },
	{ .sample = 0.9205473016275229,  .sampleWeight = 0.0663526532241763 },
	{ .sample = 1.1997100902860450,  .sampleWeight = 0.0601091352703015 },
	{ .sample = 1.5678879053053274,  .sampleWeight = 0.0520280112620429 },
	{ .sample = 2.2194097942437231,  .sampleWeight = 0.0339789420851602 },
};


uint32_t
waitForCommand(void)
{
	uint32_t command;

	/*
	 *	Set status to "waitingForCommand"
	 */
	C0HALSetStatusRegister(kSignaloidSoCStatusWaitingForCommand);

	/*
	 *	Block until command is issued
	 */
	while ((command = C0HALGetCommandRegister()) == kCalculateNoCommand) {}

	return command;
}

void
handleOperations(uint32_t command)
{
	float   inputDistributionA;
	float   inputDistributionB;
	float   result;

	/*
	 *	Set status to inform host that calculation will start
	 */
	C0HALSetStatusRegister(kSignaloidSoCStatusCalculating);

	/*
	 *	Turn on status LED
	 */
	C0HALSetLed(true);

	/*
	 *	Create distributional values from inputs
	 */
	inputDistributionA  = UxHwFloatUniformDist(kC0HALInputBufferFloat[0], kC0HALInputBufferFloat[1]);
	inputDistributionB  = UxHwFloatUniformDist(kC0HALInputBufferFloat[2], kC0HALInputBufferFloat[3]);

	/*
	 *	Calculate
	 */

	switch (command)
	{
		case kCalculateAddition:
			result = inputDistributionA + inputDistributionB;
			break;

		case kCalculateSubtraction:
			result = inputDistributionA - inputDistributionB;
			break;

		case kCalculateMultiplication:
			result = inputDistributionA * inputDistributionB;
			break;

		case kCalculateDivision:
			result = inputDistributionA / inputDistributionB;
			break;

		default:
			break;
	}

	/*
	 *	Pack result
	 */
	kC0HALOutputBufferUint32[0] = 1;
	kC0HALOutputBufferUint32[1] = UxHwFloatDistributionToByteArray(
		result,
		(uint8_t *) kC0HALOutputBufferUint8 + sizeof(uint32_t) + sizeof(uint32_t),
		kC0HALOutputBufferUint8Length - sizeof(uint32_t) - sizeof(uint32_t)
	);

	/*
	 *	Turn off status LED
	 */
	C0HALSetLed(false);

	/*
	 *	Set status
	 */
	C0HALSetStatusRegister(kSignaloidSoCStatusDone);
}

void
handleSampling(void)
{
	float generatedDistribution = UxHwFloatDistFromWeightedSamples(weightedSamples, kWeightedSampleCount);

	/*
	 *	Set status to inform host that calculation will start
	 */
	C0HALSetStatusRegister(kSignaloidSoCStatusCalculating);

	/*
	 *	Turn on status LED
	 */
	C0HALSetLed(true);

	UxHwFloatSampleBatch(generatedDistribution, (float *) kC0HALOutputBufferFloat, kC0HALInputBufferUint32[0]);

	/*
	 *	Turn off status LED
	 */
	C0HALSetLed(false);

	/*
	 *	Set status
	 */
	C0HALSetStatusRegister(kSignaloidSoCStatusDone);
}

void
handleCommand(uint32_t command)
{
	switch (command)
	{
		/*
		 *	All of the following commands parse the inputs in the same way
		 */
		case kCalculateAddition:
		case kCalculateSubtraction:
		case kCalculateMultiplication:
		case kCalculateDivision:
			handleOperations(command);
			break;

		case kCalculateSample:
			handleSampling();
			break;

		default:
			C0HALSetStatusRegister(kSignaloidSoCStatusInvalidCommand);
			break;
	}
}

void
waitForIdle(void)
{
	/*
	 *	Block until command is cleared
	 */
	while (C0HALGetCommandRegister() != kCalculateNoCommand) {}
}

int
main(void)
{
	while (1)
	{
		uint32_t command = waitForCommand();
		handleCommand(command);
		waitForIdle();
	}
}
